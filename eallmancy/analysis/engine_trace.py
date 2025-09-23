
import networkx as nx
import itertools

from eallmancy.artifacts.artifact import Artifact
from eallmancy.evaluation.evaluation import Evaluation
from eallmancy.analysis.analysis_cache import AnalysisCache
from eallmancy_gui.gui_handler import GUIHandler
from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path

from threading import Lock, Thread
import pickle as pk


@dataclass
class StaticProblemSpec:
    description: str
    template: str
    entrypoint: str
    maximization: bool
    eval_timeout: int

    @classmethod
    def from_problem_spec(cls, ps):
        return cls(
            ps.description, ps.template, ps.entrypoint, ps.maximization, ps.eval_timeout
        )


class EngineTrace:
    def __init__(self, problem_spec=None, **kwargs):
        self._id_generator = itertools.count()
        self.problem_spec = problem_spec if problem_spec is None else StaticProblemSpec.from_problem_spec(problem_spec)
        self.trace_graph = nx.DiGraph()
        self.trace_list = []
        self.lock = Lock()

        self.analysis_cache = AnalysisCache()
        self.gui_handler = GUIHandler(snapshot=self._return_self)

    def _return_self(self):
        return self

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
            
        if self.trace_analysis is not None:
            self.trace_analysis.hook(self)
     
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
        if hasattr(self, 'analysis_cache') and self.analysis_cache.segment is not None:
            self.analysis_cache.segment._trace = None
        with open(path, 'wb') as f:
            pk.dump(self, f)
        if hasattr(self, 'analysis_cache'):
            self.analysis_cache.segment._trace = self

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            trace: EngineTrace = pk.load(f)
        trace.lock = Lock()
        if hasattr(trace, 'analysis_cache') and trace.analysis_cache.segment is not None:
            trace.analysis_cache.segment = trace
        return trace

