
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact
from typing import List
import networkx as nx
from statistics import median

import numpy as np
import math

from experiments.scievo.base import ThoughtfulSolution
from experiments.scievo.population import Population



async def selection(pop: Population, k: int):
    async with pop.lock:
        funcs = [f for f in pop._members() if not math.isinf(f.evaluation.fitness)]
        if funcs == []:
            return [np.random.choice(pop._members()) for _ in range(k)]
        else:
            func = sorted(funcs, key=lambda f: f.evaluation.fitness, reverse=False)
            p = np.array([1 / (r + len(func)) for r in range(len(func))])
            p /= np.sum(p)
            return [np.random.choice(func, p=p) for _ in range(k)]

def _fitnessrank_probs(size):
    p = np.array([1 / (r + size) for r in range(size)])
    p /= np.sum(p)
    return p

def _children(gr: nx.DiGraph, nds, n):
    res = []
    for kn in gr.successors(n):
        res.append(nds[kn])
    return res

def _parents(gr: nx.DiGraph, nds, n):
    res = []
    for kn in gr.predecessors(n):
        res.append(nds[kn])
    return res

