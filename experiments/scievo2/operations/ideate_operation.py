
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
from eallmancy.analysis.trace_analysis.idea_distillation import DistilledIdea




def _solutions_block(parents):
    return '\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parents)])

def _code_blocks(parts):
    return '\n\n'.join([f'```\n{x}\n```' for x in parts])

class IdeateDivergentOperation(Operation):
    async def select_parents(self, pop: Population):
        async with pop.lock:
            nodes = dict(pop.lineage_graph.nodes(data=True))

            active_ideas: List[DistilledIdea] = list(pop.idea_extractor_cache._idea_reflections.values())

            if len(active_ideas) == 0:
                raise OperationNotApplicable()
            
            return np.random.choice(
                sorted(active_ideas, key=lambda art: art.proxy_fitness(nodes), reverse=True),
                p=_fitnessrank_probs(len(active_ideas)),
                size=1,
                replace=False
            ).tolist()

    def build_prompt(self, idea: DistilledIdea):
        return f'''{self.engine._problem_spec.description}
Our team has been trying prototype implementations. One large cluster of prototypes can be described as follows:
```
{idea.analysis}
```

We want to explore new implementation approaches, and would like you to innovate a thoughtful and well reasoned new way of solving the problem.

1. First, describe your new solution and its contents in one concise paragraph boxed in <<>> (paragraph starts with <<, ends with >>).
2. Next, implement the solution accordingly while following the template below:
{_code_blocks([self.engine._problem_spec.template])}

Provide your implementation within a single solution block.
Wrap the content blocks of the solution in ``` ... ```, but do not wrap the solution description or anything else. Do not give additional explanations.'''


