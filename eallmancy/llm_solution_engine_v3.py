

import re
from typing import Dict, List, Optional

from llm4ad.tools.llm.llm_api_https import HttpsApi
from llm4ad.base.sample import SampleTrimmer

import networkx as nx
import itertools

from llm4ad.base.code import Program
from eallmancy.base.artifact import Artifact
from eallmancy.base.problem_spec import ProblemSpec
from eallmancy.base.solution import Solution
from eallmancy.base.reflection import Reflection
from eallmancy.base.evaluation import Evaluation
from eallmancy.engine_trace import EngineTrace
from threading import Lock, Thread


class _EngineSetupContext:
    def __init__(self, engine):
        self._engine: EngineV3 = engine
        self._old_sampler, self._old_pspec = [None]*2
        self._new_sampler, self._new_pspec = [None]*2
    
    def __call__(self, api_spec=None, problem_spec=None):
        if self._engine._problem_spec is None and problem_spec is None:
            raise Exception(
                "Must provide to or instantiate engine with Problem spec"
            )
        if self._engine._sampler is None and api_spec is None:
            raise Exception(
                "Must provide to or instantiate engine with API spec"
            )
        
        self._old_sampler = self._new_sampler = self._engine._sampler
        if api_spec is not None:
            self._new_sampler = SampleTrimmer(HttpsApi(**api_spec))
        
        self._old_pspec = self._new_pspec = self._engine._problem_spec
        if problem_spec is not None:
            self._new_pspec = problem_spec
        return self

    def __enter__(self):
        self._engine._sampler = self._new_sampler
        self._engine._problem_spec = self._new_pspec

    def __exit__(self, type, value, traceback):
        self._engine._sampler = self._old_sampler
        self._engine._problem_spec = self._old_pspec



class EngineV3:
    def __init__(self, api_spec=None, problem_spec: ProblemSpec=None, debug=False, tracing=False):
        if api_spec is None:
            self._sampler = None
        else:
            self._sampler = SampleTrimmer(HttpsApi(**api_spec))
        self._problem_spec = problem_spec
        self.set = _EngineSetupContext(self)

        self._worker_pool = None

        self.trace: Optional[EngineTrace] = None

    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def __enter__(self):
        pass

    def __exit__(self):
        pass

    def start_trace(self):
        if self.trace is None:
            self.trace = EngineTrace()
        return self
    
    def dump_trace(self):
        tr = self.trace
        self.trace = None
        return tr
    
    def register_artifact(self, arte: Artifact, parents: List[Artifact] = []):
        if self.trace is not None:
            self.trace._register_trace(parents, arte)


    def generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        
        resp_txt_raw = self._sampler._llm.draw_sample(prompt) # TODO: add backoffs


        artifact: Artifact = (
            arte_class(
                response=resp_txt_raw,
                id=0 if self.trace is None else self.trace.new_id()
            )
        )

        if artifact.is_solution:
             # TODO: this will require artifact hooks and workerpool defn
            evaluation = self._worker_pool.evaluate(artifact)
            artifact.set_evaluation(evaluation)

        self.register_artifact(artifact, parents)

        return artifact
    