
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

from collections import defaultdict


def distance_act(d):
    if math.isinf(d):
        return 1
    C = 1
    return min(max(1-C/d, 0), 1)




def _solutions_block(parents):
    return '\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parents)])

def _code_blocks(parts):
    return '\n\n'.join([f'```\n{x}\n```' for x in parts])

class CrossoverOperation(Operation):
    async def select_parents(self, pop: Population):
        artifacts = {k: v for k,v in pop.lineage_graph.nodes(data='artifact') if v.is_solution and not math.isinf(v.fitness)}
        fitnesses = {k: v.fitness for k,v in artifacts.items()}
        _fitness_vals = list(fitnesses.values())
        def fitness_act(query):
            return sum(query > v for v in _fitness_vals) / len(_fitness_vals)   # percentile based transform TODO: improve

        distances = pop.heritage_distances

        marginal_score_memo = defaultdict(lambda : 0)

        cluster_members = []
        def append_remove_elem(nidx):
            cluster_members.append(nidx)
            for midx in set(artifacts.keys()).difference(cluster_members):
                ky = (max(midx,nidx), min(midx,nidx))
                marginal_score_memo[midx] += fitness_act(fitnesses[nidx]) * distance_act(distances[ky])
            del fitnesses[nidx]
            if nidx in marginal_score_memo.keys():
                del marginal_score_memo[nidx]

        k=3
        for cidx in range(2,k+1):
            if cidx > len(artifacts): break

            if cidx == 2:
                valid_dists = {(n,m): d for (n,m), d in distances.items() if n in artifacts.keys() and m in artifacts.keys()}
                npairs = len(valid_dists)
                probs = np.array([distance_act(d) * fitness_act(fitnesses[n]) * fitness_act(fitnesses[m]) for (n,m), d in valid_dists.items()])
                if probs.sum() == 0:
                    probs += 1.0   # only possible when everything is zero, activations make weakly positive
                probs = probs.astype(float) / probs.sum()
                pair_idx = np.random.choice(list(range(npairs)), p=probs)
                nidx, midx = list(valid_dists.keys())[pair_idx]
                append_remove_elem(nidx)
                append_remove_elem(midx)
            else:
                probs = np.array(list(map( lambda ts: 1.0* ts[1] * fitness_act(fitnesses[ts[0]]), marginal_score_memo.items() )))
                if probs.sum() == 0:
                    probs += 1.0   # only possible when everything is zero, activations make weakly positive
                probs = probs.astype(float) / probs.sum()
                nidx = np.random.choice(
                    list(marginal_score_memo.keys()),
                    p=probs
                )
                append_remove_elem(nidx)
        return [artifacts[i] for i in cluster_members]

    def build_prompt(self, *parents: List[Artifact]):
        return f'''{self.engine._problem_spec.description}
I have {len(parents)} existing solutions with their contents as follows:
{_solutions_block(parents)}

Please help me create a new solution that is inspired by but distinct from the existing solutions.
Attempt to combine promising approaches from the solutions which could work well together.

1. First, describe your new solution and its contents in one concise paragraph boxed in <<>> (paragraph starts with <<, ends with >>).
2. Next, improve on the following solution containing the following sections:
{_code_blocks([self.engine._problem_spec.template])}

Provide your implementation with the *same* number of content blocks as the previous solution ({1} blocks).
Wrap the content blocks of the solution in ``` ... ```, but do not wrap the solution description or anything else. Do not give additional explanations.'''

