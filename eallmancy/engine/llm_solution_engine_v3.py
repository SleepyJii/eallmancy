

import re
from typing import Dict, List, Optional

from llm4ad.tools.llm.llm_api_https import HttpsApi
from llm4ad.base.sample import SampleTrimmer

import networkx as nx
import itertools

from llm4ad.base.code import Program
from eallmancy.artifacts.artifact import Artifact
from eallmancy.engine.problem_spec import ProblemSpec
from eallmancy.artifacts.single_part_solution import SinglePartSolution
from eallmancy.engine.engine_trace import EngineTrace
from threading import Lock, Thread

from eallmancy.artifacts.multi_part_solutions import (
    MultiPartSolution, DiffSolution, DummyMultiPartSolution
)
from eallmancy.evaluation import (
    EvaluationWorkerPool,
    PythonEvaluationWorker, GitEvaluationWorker, Evaluation
)
from eallmancy.engine.problem_specs import EvolveGitSpec


class EngineSetupContext:
    def __init__(self, engine):
        self._engine: EngineV3 = engine
        self._old_sampler, self._old_pspec = [None]*2
        self._new_sampler, self._new_pspec = [None]*2
        self._trace = None  # used as a holder if engine completes first
    
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
        self._trace = None
        self._engine._sampler = self._new_sampler
        self._engine._problem_spec = self._new_pspec
        self._engine.start()
        return self

    def __exit__(self, type, value, traceback):
        self._engine._sampler = self._old_sampler
        self._engine._problem_spec = self._old_pspec
        self._engine.finish()
    
    @property
    def trace(self):
        if self._trace is not None:
            return self._trace
        return self._engine.trace



class EngineV3:
    def __init__(self, api_spec=None, problem_spec: ProblemSpec=None, debug=False, tracing=False):
        if api_spec is None:
            self._sampler = None
        else:
            self._sampler = SampleTrimmer(HttpsApi(**api_spec))
        self._problem_spec = problem_spec
        self.set = EngineSetupContext(self)

        self._worker_pool = None

        self.trace: Optional[EngineTrace] = None
        self.is_running = False
        self.hooks = []

    def add_hook(self, hook_func):
        self.hooks.append(hook_func)
        return self

    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def start(self):
        if not self.is_ready():
            raise Exception("engine does not have both API and ProblemSpec! cannot start")

        self._worker_pool = EvaluationWorkerPool(
            GitEvaluationWorker if (type(self._problem_spec) is EvolveGitSpec) else PythonEvaluationWorker,
            ps=self._problem_spec,
            n_workers=1 # waiting on impl
        ).setup()

        self.start_trace()
        self.is_running = True
    
    def finish(self):
        self._worker_pool = None # this should implicitly call __del__ on the workerpool
        self.is_running = False
        return self.dump_trace()

    def start_trace(self):
        if self.trace is None:
            self.trace = EngineTrace()
        return self
    
    def dump_trace(self):
        tr = self.trace
        self.trace = None
        return tr
    
    def register_artifact(self, arte: Artifact, parents: List[Artifact] = []):
        if not self.is_running:
            raise Exception("cannot generate artifact when the engine has not been started!")
        
        if self.trace is not None:
            self.trace._register_trace(parents, arte)
            for hook in self.hooks:
                hook(self.trace)


    def generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        if not self.is_running:
            raise Exception("cannot generate artifact when the engine has not been started!")
        
        resp_txt_raw = self._sampler._llm.draw_sample(prompt) # TODO: add backoffs


        artifact: Artifact = (
            arte_class(
                query=prompt,
                response=resp_txt_raw,
                id=0 if self.trace is None else self.trace.new_id()
            )
        )

        if issubclass(arte_class, MultiPartSolution):
            if issubclass(arte_class, DiffSolution) and artifact.parent is None:
                artifact: DiffSolution = artifact.set_parent(DummyMultiPartSolution(self._problem_spec.section_templates))
            evaluation = self._worker_pool.evaluate_solution(artifact)
            artifact = artifact.set_evaluation(evaluation)

        self.register_artifact(artifact, parents)

        return artifact
    