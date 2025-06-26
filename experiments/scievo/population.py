
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact

from eallmancy import SinglePartSolution, ProblemSpec
from typing import List
import os
import re
from asyncio import Lock
import math

import numpy as np
import networkx as nx

from experiments.scievo.operations.utils import ancestor_mapdists, latest_common_ancestor, heritage_distance, heritage_distances


class Population:
    def __init__(self, init_members=[], max_samples=100, max_generations=100):

        self.lock = Lock()
        self.max_samples, self.max_generations = max_samples, max_generations

        self.lineage_graph = nx.DiGraph()
        self.ancestor_mapdists = dict()
        self.heritage_distances = dict()
        for m in init_members:
            self._register(m, [], operation_name='preload')

    def _members(self) -> List[Artifact]:
        return list(map(lambda ts: ts[1], self.lineage_graph.nodes(data='artifact')))

    async def members(self) -> List[Artifact]:
        async with self.lock:
            return self._members()
    
    async def size(self):
        async with self.lock:
            return len(self.lineage_graph.nodes())

    def _register(self, art, parents, **attr):
        self.lineage_graph.add_node(
            art.trace_id,
            artifact=art,
            **attr
        )
        for par in parents:
            if par is not None:
                self.lineage_graph.add_edge(par.trace_id, art.trace_id)

        if art.is_solution:

            # update localized averages for refine operation
            if math.isinf(art.fitness):
                local_fitness_sum, local_fitness_cnt = 0, 0
            else:
                local_fitness_sum, local_fitness_cnt = art.fitness, 1
            all_nodes = self.lineage_graph.nodes(data=True)
            for nghbr_id, dist in nx.single_source_shortest_path_length(self.lineage_graph, art.trace_id, cutoff=1).items():
                nghbr_ddict = all_nodes[nghbr_id]
                if nghbr_id == art.trace_id:
                    continue
                if nghbr_ddict['artifact'].is_solution:
                    nghbr_ddict['refine_fitness_sum'] += art.fitness
                    nghbr_ddict['refine_fitness_cnt'] += 1
                    if not math.isinf(nghbr_ddict['artifact']):
                        local_fitness_sum += nghbr_ddict['artifact'].fitness
                        local_fitness_cnt += 1
            all_nodes[art.trace_id]['refine_fitness_sum'] = local_fitness_sum
            all_nodes[art.trace_id]['refine_fitness_cnt'] = local_fitness_cnt

            # update heritage distances
            self.ancestor_mapdists[art.trace_id] = {
                b: nx.shortest_path_length(self.lineage_graph, source=b, target=art.trace_id)
                for b in nx.ancestors(self.lineage_graph, art.trace_id).union({art.trace_id})
            }
            for _m in self.lineage_graph.nodes:
                if _m != art.trace_id:
                    n, m = max(art.trace_id, _m), min(art.trace_id, _m)
                    self.heritage_distances[(n,m)] = heritage_distance(self.lineage_graph, self.ancestor_mapdists, n, m)

    async def register(self, *args, **kwargs):
        async with self.lock:
            self._register(*args, **kwargs)
    
    async def is_full(self):
        return (await self.size()) > self.max_samples

