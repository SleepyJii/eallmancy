
import networkx as nx
import itertools

from eallmancy.artifacts.artifact import Artifact
from eallmancy.evaluation.evaluation import Evaluation
from eallmancy.analysis.trace_analysis import TraceAnalysis
from typing import Dict, List
from pathlib import Path

from threading import Lock, Thread
import pickle as pk



class EngineTrace:
    def __init__(self, problem_spec, trace_analysis=False, **kwargs):
        self._id_generator = itertools.count()
        self.problem_spec = problem_spec
        self.trace_graph = nx.DiGraph()
        self.trace_list = []
        self.lock = Lock()

        self.trace_analysis = None if not trace_analysis else TraceAnalysis(ps=problem_spec, **kwargs)

    @property
    def graph(self):
        return self.trace_graph
    
    def __getitem__(self, k):
        with self.lock:
            return self.trace_graph.nodes(data='artifact')[k]
    
    @property
    def list(self):
        return self.trace_list

    def new_id(self):
        return next(self._id_generator)

    def _register_trace(self, input_arts, output_art, prompt_builder_name='', **tags):
        with self.lock:
            self.trace_list.append(output_art)
            self.trace_graph.add_node(
                output_art.trace_id,
                artifact=output_art,
                **tags
            )
            for inp_art in input_arts:
                if inp_art is not None:
                    self.trace_graph.add_edge(inp_art.trace_id, output_art.trace_id)
     
    def register_artifact(self, arte: Artifact, parents: List[Artifact] = []):
        if arte.trace_id is not None:
            raise Exception('attempted to register Artifact which already had id {arte.trace_id}')
        arte.set_id(next(self._id_generator))
        self._register_trace(
            input_arts=parents,
            output_art=arte,
        )

    def save(self, path):
        self.lock = None # lock is unpickleable
        Path(path).parent.mkdir(exist_ok=True, parents=True)
        with open(path, 'wb') as f:
            pk.dump(self, f)

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            trace: EngineTrace = pk.load(f)
        trace.lock = Lock()
        return trace

