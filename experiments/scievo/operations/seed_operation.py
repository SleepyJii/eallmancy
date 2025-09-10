
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


class SeedOperation(Operation):
    
    async def select_parents(self, pop: Population):
        return []

    def build_prompt(self, *parents: List[Artifact]):
        return f'''{self.engine._problem_spec.description}
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>. 
2. Next, implement the following Python function:
{self.engine._problem_spec.template}
Enclose your implementation within a code block like ```python ... ```, but make sure to put the description outside of it. Do not give additional explanations.'''

