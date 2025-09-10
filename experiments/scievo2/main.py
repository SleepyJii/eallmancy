
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact

from eallmancy import SinglePartSolution, ProblemSpec
from eallmancy.evaluation import Evaluation
from typing import List
import os
import re

from experiments.scievo.base import ThoughtfulSolution
from experiments.scievo2.population import Population

from experiments.scievo2.operations.operation import Operation, OperationNotApplicable
# from experiments.scievo.operations.utils import selection
from experiments.scievo2.operations.repair_operation import RepairOperation
from experiments.scievo2.operations.seed_operation import SeedOperation
from experiments.scievo2.operations.refine_operation import RefineOperation
from experiments.scievo2.operations.crossover_operation import CrossoverOperation
from experiments.scievo2.operations.ideate_operation import IdeateDivergentOperation



# INIT_ART = ThoughtfulSolution("""
# <<The algorithm selects the next node based on the minimum average distance to all unvisited nodes, prioritizing nodes that minimize the overall travel distance from the current node while also considering the distances to the remaining unvisited nodes.>>              
# ```
# import numpy as np

# def select_next_node(current_node: int, destination_node: int, unvisited_nodes: np.ndarray, distance_matrix: np.ndarray) -> int:
#     min_average_distance = float('inf')
#     next_node = unvisited_nodes[0]
    
#     for node in unvisited_nodes:
#         total_distance = 0
#         for other_node in unvisited_nodes:
#             if node != other_node:
#                 total_distance += distance_matrix[node, other_node]
#         average_distance = total_distance / (len(unvisited_nodes) - 1)
        
#         if average_distance < mni_average_distance:
#             min_average_distance = average_distance
#             next_node = node
            
#     return next_node
# ```
# """).set_id(-1).set_evaluation(
#                 Evaluation(
#                     fitness = float('-inf'),
#                     errors = str("Undefined variable `mni_average_distance`")
#                 )
#             )




class SciEvo:
    
    def __init__(self, api, ps, engine: EngineV3 = None, op_freqs=dict(), config=dict()): 
        if engine is None:
            self.engine = EngineV3()
        else:
            self.engine = engine
        self.api, self.ps = (api, ps)
        self.seed_operation = SeedOperation(self.engine)
        
        self.repeat_operations = dict(
            repair=(
                RepairOperation(self.engine), op_freqs.get('repair', 1)
            ),
            refine=(
                RefineOperation(self.engine), op_freqs.get('refine', 4)
            ),
            crossover=(
                CrossoverOperation(self.engine), op_freqs.get('crossover', 1)
            ),
            ideate_divergent=(
                IdeateDivergentOperation(self.engine), op_freqs.get('ideate_divergent', 1)
            ),
        )
        self.config = dict(
            max_samples=30,
            max_generations=int(1e9),
            initial_samples=5,
            ignore_jplag_api_status=config.get('ignore_jplag_checking', True),
        )
        self.config.update(config)


    async def run(self):

        original_engine_hooks = self.engine.hooks

        with self.engine.set(problem_spec=self.ps, api_spec=self.api) as ec: 
            

            population = Population(
                self.engine,
                **self.config
            )

            self.engine.hooks.append(population.hook)
            

            # use seed operation for initial membership
            await self.seed_operation.apply(population, n=self.config['initial_samples'])

            while not await population.is_full():
                for operation, num_apply in self.repeat_operations.values():
                    for _ in range(num_apply):
                        await operation.apply(population)

            self.engine.hooks = original_engine_hooks
            return max((await population.members()), key=lambda f: f.fitness), population, ec.trace


