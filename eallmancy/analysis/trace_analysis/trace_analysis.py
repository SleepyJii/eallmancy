
from eallmancy import Artifact
from eallmancy import SinglePartSolution, ProblemSpec

from eallmancy.analysis.utils import ancestor_mapdists, latest_common_ancestor, heritage_distance, heritage_distances
from eallmancy.analysis.trace_analysis.idea_extractor import IdeaExtractorCache

from typing import List
import os
import re
from asyncio import Lock
import math
from collections import defaultdict
import numpy as np
import networkx as nx


def _DEFAULT_FITNESS_STATS():
    return {'refine_fitness_sum': 0, 'refine_fitness_cnt': 0}

class TraceAnalysis:
    def __init__(self, **kwargs):

        self.lock = Lock()

        # general stats
        self.last_seen_solutions = []
        self.last_seen_graph = nx.DiGraph()

        # localized fitness memoization
        self.local_fitness_stats = defaultdict(_DEFAULT_FITNESS_STATS)

        # heritage distance memoization
        self.ancestor_mapdists = dict()
        self.heritage_distances = dict()

        # idea extractor internal cache
        self.idea_extractor_cache = IdeaExtractorCache(**kwargs)
        self.idea_extraction_radius = kwargs.get('max_match_heritagedist', 3)


    def _members(self) -> List[Artifact]:
        return self.last_seen_solutions

    async def members(self) -> List[Artifact]:
        async with self.lock:
            return self._members()
    
    async def size(self):
        async with self.lock:
            return len(self.last_seen_solutions)
    
    @property
    def lineage_graph(self):
        return self.last_seen_graph

    def update_localized_fitnesses(self, ttrace):

        art = ttrace.list[-1] ## TODO: better way to handle this

        if art.is_solution:
            non_soln_nodes = {n for n, d in ttrace.graph.nodes(data=True) if not d['artifact'].is_solution}
            soln_only_G = ttrace.graph.subgraph(set(ttrace.graph.nodes)-non_soln_nodes)

            # update localized averages for refine operation
            if math.isinf(art.fitness):
                local_fitness_sum, local_fitness_cnt = 0, 0
            else:
                local_fitness_sum, local_fitness_cnt = art.fitness, 1
            all_nodes = soln_only_G.nodes(data=True)
            for nghbr_id, dist in nx.single_source_shortest_path_length(soln_only_G, art.trace_id, cutoff=1).items():
                nghbr_ddict = all_nodes[nghbr_id]
                if nghbr_id == art.trace_id:
                    continue
                if nghbr_ddict['artifact'].is_solution:
                    self.local_fitness_stats[nghbr_id]['refine_fitness_sum'] += art.fitness
                    self.local_fitness_stats[nghbr_id]['refine_fitness_cnt'] += 1
                    if not math.isinf(nghbr_ddict['artifact'].fitness):
                        local_fitness_sum += nghbr_ddict['artifact'].fitness
                        local_fitness_cnt += 1

            # TODO: change the setting here to be on some internal variable
            self.local_fitness_stats[art.trace_id]['refine_fitness_sum'] = local_fitness_sum
            self.local_fitness_stats[art.trace_id]['refine_fitness_cnt'] = local_fitness_cnt
        

    def update_heritage_distances(self, ttrace):

        art = ttrace.list[-1] ## TODO: better way to handle this

        if art.is_solution:
            non_soln_nodes = {n for n, d in ttrace.graph.nodes(data=True) if not d['artifact'].is_solution}
            soln_only_G = ttrace.graph.subgraph(set(ttrace.graph.nodes)-non_soln_nodes)

            # update heritage distances
            self.ancestor_mapdists[art.trace_id] = {
                b: nx.shortest_path_length(soln_only_G, source=b, target=art.trace_id)
                for b in nx.ancestors(soln_only_G, art.trace_id).union({art.trace_id})
            }
            for _m in soln_only_G.nodes:
                if _m != art.trace_id:
                    n, m = max(art.trace_id, _m), min(art.trace_id, _m)
                    self.heritage_distances[(n,m)] = heritage_distance(soln_only_G, self.ancestor_mapdists, n, m)
    

    def update_idea_extraction(self, ttrace):
        # lookup heritage distance to latest artifact

        art = ttrace.list[-1] ## TODO: better way to handle this
        # find heritage radius to artifact


        ## TODO: solution filtered graph
        local_neighborhood = list(set(
            [
                {a,b}.difference({art.trace_id}).pop() 
                for (a,b), d in self.heritage_distances.items()
                if art.trace_id in {a,b} and d < self.idea_extraction_radius
            ] + [art.trace_id]
        ))

        self.idea_extractor_cache.hook(art, ttrace, solution_id_filter=local_neighborhood)

    @property
    def distilled_ideas(self):
        return self.idea_extractor_cache._idea_reflections

    def hook(self, ttrace):
        ## THIS IS WHAT WE WILL GET EVERY TIME A TRACE UPDATES
        new_art = ttrace.list[-1]
        print(f'TAhook {new_art.trace_id}')
        
        self.update_localized_fitnesses(ttrace)

        self.update_heritage_distances(ttrace)

        if new_art.is_solution:
            print('\t',self.ancestor_mapdists[new_art.trace_id])

        self.update_idea_extraction(ttrace)

        self.last_seen_solutions = [a for a in ttrace.list if a.is_solution]

        # non_soln_nodes = {n for n, d in ttrace.graph.nodes(data=True) if not d['artifact'].is_solution}
        # soln_only_G = ttrace.graph.subgraph(set(ttrace.graph.nodes)-non_soln_nodes)
        self.last_seen_graph = ttrace.graph



