

import re
from typing import Dict, List, Optional

from llm4ad.tools.llm.llm_api_https import HttpsApi
from llm4ad.tools.llm.llm_api_openai import OpenAIAPI
from llm4ad.base.sample import SampleTrimmer

import networkx as nx
import numpy as np
import random
import itertools
import inspect

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
    EvaluationWorkerPool, QualitativeEvaluationWorker,
    PythonEvaluationWorker, GitEvaluationWorker, Evaluation
)
import asyncio
from eallmancy.engine.evolve_git_spec import EvolveGitSpec
from eallmancy.engine.evolve_qualitative_spec import EvolveQualitativeSpec

def _filter_openai_kwargs(api_spec):
    return {k:v for k,v in api_spec.items() if k in ['base_url', 'api_key', 'model', 'timeout']}

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
            if api_spec.get('openai_format', False):
                self._new_sampler = SampleTrimmer(OpenAIAPI(**_filter_openai_kwargs(api_spec)))
            else:
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
        print("ENGINE STARTED, PS set to", self._new_pspec)
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

class APIKwargsContext:
    def __init__(self, llm, **new_kwargs):
        self.old_kwargs = {k:v for k,v in llm.kwargs.items()}
        self.modified_llm = llm
        self.kwargs = new_kwargs
    
    def __enter__(self):
        self.modified_llm.kwargs.update(self.kwargs)
    
    def __exit__(self, type, value, traceback):
        self.modified_llm.kwargs = self.old_kwargs
        self.modified_llm = None
        self.old_kwargs = None


DEFAULT_TEMPERATURE = 0.7

class EngineV3:
    def __init__(self, api_spec=None, problem_spec: ProblemSpec=None, tracing=True, debug=False, **kwargs):
        if api_spec is not None:
            if api_spec.get('openai_format', False):
                self._sampler = SampleTrimmer(OpenAIAPI(**_filter_openai_kwargs(api_spec)))
            else:
                self._sampler = SampleTrimmer(HttpsApi(**api_spec))
        else:
            self._sampler = None
        
        self._problem_spec = problem_spec
        self.set = EngineSetupContext(self)

        self._worker_pool = None

        self.trace: Optional[EngineTrace] = None
        self._tracing = tracing
        self.is_running = False
        self.hooks = []
        self.kwargs = kwargs

    def add_hook(self, hook_func):
        self.hooks.append(hook_func)
        return self

    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def start(self):
        if not self.is_ready():
            raise Exception("engine does not have both API and ProblemSpec! cannot start")

        if type(self._problem_spec) is EvolveGitSpec:
            self._worker_pool = EvaluationWorkerPool(
                GitEvaluationWorker,
                ps=self._problem_spec,
                n_workers=1 # waiting on impl
            ).setup()
        elif type(self._problem_spec) is EvolveQualitativeSpec:
            self._worker_pool = EvaluationWorkerPool(
                QualitativeEvaluationWorker,
                ps=self._problem_spec,
                n_workers=1
            ).setup()
        else:
            self._worker_pool = EvaluationWorkerPool(
                PythonEvaluationWorker,
                ps=self._problem_spec,
                n_workers=1
            ).setup()

        if self._tracing:
            self.start_trace()
        self.is_running = True
    
    def finish(self):
        self._worker_pool = None # this should implicitly call __del__ on the workerpool
        self.is_running = False
        return self.dump_trace()

    def start_trace(self):
        if self.trace is None:
            self.trace = EngineTrace(problem_spec=self._problem_spec, **self.kwargs)
        return self
    
    def dump_trace(self):
        tr = self.trace
        self.trace = None
        return tr
    
    def register_artifact(self, arte: Artifact, parents: List[Artifact] = [], disable_hooks=False, **tags):
        if not self.is_running:
            raise Exception("cannot generate artifact when the engine has not been started!")
        
        if self.trace is not None:
            self.trace._register_trace(parents, arte, **tags)
            if not disable_hooks:
                for hook in self.hooks:
                    hook(arte, self.trace)
        
    async def async_register_artifact(self, arte: Artifact, parents: List[Artifact] = [], disable_hooks=False, **tags):
        if not self.is_running:
            raise Exception("cannot generate artifact when the engine has not been started!")
        
        if self.trace is not None:
            self.trace._register_trace(parents, arte, **tags)
            if not disable_hooks:
                for hook in self.hooks:
                    if inspect.iscoroutinefunction(hook):
                        # because we are in async mode, assuming async hooks
                        await hook(arte, self.trace)
                    else:
                        hooK(arte, self.trace)


    def build_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True, **kwargs):
        if not self.is_running:
            raise Exception("cannot generate artifact when the engine has not been started!")
        
        with APIKwargsContext(self._sampler._llm, **kwargs):
            resp_txt_raw = self._sampler._llm.draw_sample(prompt) # TODO: add backoffs

        artifact: Artifact = (
            arte_class(
                response=resp_txt_raw,
                id=0 if self.trace is None else self.trace.new_id()
            )
            .set_query(prompt)
        )

        if issubclass(arte_class, MultiPartSolution):
            if issubclass(arte_class, DiffSolution) and artifact.parent is None:
                artifact: DiffSolution = artifact.set_parent(DummyMultiPartSolution(self._problem_spec.section_templates))
            evaluation = self._worker_pool.evaluate_solution(artifact)
            artifact = artifact.set_evaluation(evaluation)
        return artifact, parents


    def generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True, **kwargs):

        if self.kwargs.get('thermal_chaos', False):
            # this should randomize temperature via APIKwargsContext
            kwargs.update({'temperature': random.random()*1.75})
        else:
            kwargs.update({'temperature': self._sampler._llm.kwargs.get('temperature', DEFAULT_TEMPERATURE)})

        artifact, parents = self.build_artifact(prompt, arte_class, parents, **kwargs)

        if register:
            self.register_artifact(artifact, parents, **kwargs)

        return artifact
    
    async def async_build_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True, **kwargs):
        return await asyncio.to_thread(self.build_artifact, prompt, arte_class, parents, **kwargs)

    async def async_generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True, **kwargs):
        artifact, parents = await self.async_build_artifact( prompt, arte_class, parents, **kwargs)

        if register:
            await self.async_register_artifact(artifact, parents, **kwargs)

        return artifact
    