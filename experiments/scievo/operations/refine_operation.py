
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact
from typing import List
import numpy as np
import networkx as nx
import math
from statistics import median

from experiments.scievo.base import ThoughtfulSolution
from experiments.scievo.population import Population
from experiments.scievo.operations.operation import Operation, OperationNotApplicable
from experiments.scievo.operations.utils import _children, _parents, _fitnessrank_probs




def _solutions_block(parents):
    return '\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parents)])

def _code_blocks(parts):
    return '\n\n'.join([f'```\n{x}\n```' for x in parts])

class RefineOperation(Operation):

    async def select_parents(self, pop: Population):
        async with pop.lock:
            nodes = pop.lineage_graph.nodes(data=True)

            _soln_nodes = [(n, ddict) for (n, ddict) in nodes if ddict['artifact'].is_solution]

            _localavg_sorted_nodes = [(n,ddict) for (n, ddict) in _soln_nodes if ddict['refine_fitness_cnt']!=0]
            _localavg_sorted_nodes = list(sorted(_localavg_sorted_nodes, key=lambda ts: ts[1]['refine_fitness_sum'] / ts[1]['refine_fitness_cnt']))

            if len(_localavg_sorted_nodes) == 0:
                # print(f'\t[cancel_refine] solns:{len(_soln_nodes)} validavg: {len(_localavg_sorted_nodes)}')
                raise OperationNotApplicable()
            # else:
                # print('\t[startt_refine]')

            centroid_nde = np.random.choice([ts[0] for ts in _localavg_sorted_nodes], p=_fitnessrank_probs(len(_localavg_sorted_nodes)))
            local_nghbrs = [nodes[nghbr_id]['artifact'] for nghbr_id, dist in nx.single_source_shortest_path_length(pop.lineage_graph, centroid_nde, cutoff=1).items()]
            local_nghbrs = [a for a in local_nghbrs if not math.isinf(a.fitness)]
            return np.random.choice(
                local_nghbrs,
                p=_fitnessrank_probs(len(local_nghbrs)),
                size=min(len(local_nghbrs), self.kwargs.get('refine_local_nghbrs', 3)),
                replace=False
            ).tolist()

    def build_prompt(self, *parents: List[Artifact]):
        return f'''{self.engine._problem_spec.description}
I have {len(parents)} existing solutions with their contents as follows:
{_solutions_block(parents)}

Please help me create a new implementation that is inspired by but distinct from the existing solutions.
Try to improve and innovate on the approaches taken in them that seem successful.

1. First, describe your new solution and its contents in one concise paragraph boxed in <<>> (paragraph starts with <<, ends with >>).
2. Next, implement the solution accordingly while following the template below:
{_code_blocks([self.engine._problem_spec.template])}

Provide your implementation with the *same* number of content blocks as the previous solution ({1} blocks).
Wrap the content blocks of the solution in ``` ... ```, but do not wrap the solution description or anything else. Do not give additional explanations.'''

