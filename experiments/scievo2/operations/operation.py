
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact
from typing import List
import networkx as nx
from statistics import median

from experiments.scievo2.base import ThoughtfulSolution
from experiments.scievo2.population import Population



class OperationNotApplicable(Exception): pass

class Operation:
    def __init__(self, engine: EngineV3, **kwargs):
        self.engine = engine
        self.kwargs = kwargs
        self.times_applied = 0

    async def apply(self, pop: Population, n: int = 1, **kwargs):
        for _ in range(n):
            try:
                parents = await self.select_parents(pop, **kwargs)
                prmpt = self.build_prompt(*parents, **kwargs)
                art, parents = await self.engine.async_build_artifact(prmpt, ThoughtfulSolution, parents=parents)
                await self.engine.async_register_artifact(art, parents, operation_name=self.__class__.__name__)
            except OperationNotApplicable as e:
                return
    
    async def is_applicable(self, pop: Population, **kwargs):
        return True

    async def select_parents(self, pop: Population, **kwargs) -> List[Artifact]:
        pass

    def build_prompt(self, *parents: List[Artifact], **kwargs):
        pass
    