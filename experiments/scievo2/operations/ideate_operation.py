
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



class IdeateOperation(Operation):
    async def select_parents(self, pop: Population):
        pass

    def build_prompt(self, *parents: List[Artifact]):
        pass

