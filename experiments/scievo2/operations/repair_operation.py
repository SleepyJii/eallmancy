
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact
from typing import List
import numpy as np
import networkx as nx
import math
from statistics import median

from experiments.scievo2.base import ThoughtfulSolution
from experiments.scievo2.population import Population
from experiments.scievo2.operations.operation import Operation, OperationNotApplicable
from experiments.scievo2.operations.utils import _children, _parents, _fitnessrank_probs




def _solutions_block(parents):
    return '\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parents)])

def _code_blocks(parts):
    return '\n\n'.join([f'```\n{x}\n```' for x in parts])

class RepairOperation(Operation):
    async def select_parents(self, pop: Population):
        async with pop.lock:
            nodes = pop.lineage_graph.nodes(data=True)

            # filter out past repairs
            _nonrepair_nodes = [(n, ddict) for (n, ddict) in nodes if ddict['operation_name'] != 'RepairOperation']

            # filter to solutions with failures
            _failed_nodes = [(n, ddict) for (n, ddict) in _nonrepair_nodes if ddict['artifact'].is_solution and math.isinf(ddict['artifact'].fitness)]

            # filter to solutions with no more than X repair children
            def count_repair_operations(nde):
                return len([
                    nbr_ddict
                    for nbr_ddict in _children(pop.lineage_graph, nodes, nde)
                    if nbr_ddict['operation_name'] == 'RepairOperation'
                ])

            _valid_torepair_nodes = [(n, ddict) for (n, ddict) in _failed_nodes if count_repair_operations(n) < self.kwargs.get('repair_max_attempts', 1)]
            if len(_valid_torepair_nodes) == 0:
                # print(f'\t[cancel_repair] nonrep:{len(_nonrepair_nodes)} failed:{len(_failed_nodes)} valid:{len(_valid_torepair_nodes)}')
                raise OperationNotApplicable()
            # else:
            #     print('\t[startt_repair]')

            # show preference to higher parental average fitnesses
            # if no valid examples for median, just use 0
            _median_noninf_fitness = median([ddict['artifact'].fitness for (n, ddict) in nodes if ddict['artifact'].is_solution and not math.isinf(ddict['artifact'].fitness)] or [0])
            def avg_parent_fitness(nde):
                f_ls = [nnd['artifact'].fitness for nnd in _parents(pop.lineage_graph, nodes, nde)]
                if len(f_ls) == 0:
                    return _median_noninf_fitness
                else:
                    return sum(f_ls) / len(f_ls)

            _nodes = list(sorted(_valid_torepair_nodes, key=lambda ts: avg_parent_fitness(ts[0]), reverse=True))
            _arts = [ddict['artifact'] for (_, ddict) in _nodes]
            return [np.random.choice(_arts, p=_fitnessrank_probs(len(_arts)))]

    def build_prompt(self, *parents: List[Artifact]):
        parent_soln = parents[0]
        return f'''{self.engine._problem_spec.description}
I have an solutions with content as follows:
Artifact {parent_soln.trace_id}
Algorithm: {parent_soln.thought}
{parent_soln.program}

Which is meant to match the following template
{_code_blocks([self.engine._problem_spec.template])}

But is currently throwing an Evaluation error:
Evaluation: {parent_soln.evaluation if parent_soln.evaluation is not None else 'None'}

Based on the solution description, its code and the error raised, fix the solution such that it no longer errors.

Wrap the content blocks of the solution in ``` ... ```. Do not give additional explanations.'''

    async def apply(self, pop: Population, n: int = 1, **kwargs):
        for _ in range(n):
            try:
                parent_to_repair, = await self.select_parents(pop, **kwargs)
                prmpt = self.build_prompt(parent_to_repair, **kwargs)
                art, _ = await self.engine.async_build_artifact(prmpt, ThoughtfulSolution, parents=[parent_to_repair])
                art.thought = parent_to_repair.thought
                await self.engine.async_register_artifact(art, [parent_to_repair], operation_name=self.__class__.__name__)
            except OperationNotApplicable as e:
                return
    
    