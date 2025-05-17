

import re
from typing import Dict

from llm4ad.tools.llm.llm_api_https import HttpsApi
from llm4ad.base.sample import SampleTrimmer

import networkx as nx
import itertools

from llm4ad.base.code import Program
from reallm.base.artifact import Artifact
from reallm.base.problem_spec import ProblemSpec
from reallm.base.solution import Solution
from reallm.base.reflection import Reflection
from reallm.base.evaluation import Evaluation

from threading import Lock, Thread


class _PromptToArtifactConverter:
    def __init__(self, engine, addons=dict(), artifact_class=Artifact, debug=False):
        self._engine = engine
        self._addons: Dict[str, re.Pattern] = addons
        self._debug = debug
        self._artifact_class = artifact_class
    
    @property
    def _kwargs(self):
        return dict(
            engine=self._engine, addons=self._addons,
            debug=self._debug, artifact_class=self._artifact_class
        )
    
    @property
    def _is_solution(self):
        return issubclass(self._artifact_class, Solution)

    @property
    def _sampler(self) -> SampleTrimmer:
        return self._engine._sampler
    
    @property
    def _problem_spec(self) -> ProblemSpec:
        return self._engine._problem_spec

    def artifact(self, arttype):
        _kwargs = self._kwargs
        _kwargs.update(dict(artifact_class=arttype))
        return _PromptToArtifactConverter(**_kwargs)

    def as_solution(self):
        return self.artifact(Solution)

    def as_reflection(self):
        return self.artifact(Reflection)

    def add_output(self, **kwargs):
        _kwargs = self._kwargs
        _kwargs['addons'] = dict(**_kwargs['addons'], **kwargs)
        return _PromptToArtifactConverter(**_kwargs)

    def __call__(self, prompt_builder_func):
        def _sampling_func(*args, **kwargs):

            if not self._engine.is_ready():
                raise Exception(
                    "LLMSolutionEngine is not ready! Make sure its supplied with an ApiSpec and ProblemSpec"
                )

            preformatted_prompt = prompt_builder_func(*args, **kwargs)
            formatted_prompt = (
                preformatted_prompt
                .replace("<PROBLEM_DESCR>", self._problem_spec.description)
                .replace("<PROBLEM_TEMPLATE>", self._problem_spec.template)
                .replace("<PROBLEM_FUNCNAME>", self._problem_spec.entrypoint)
            )

            resp_txt_raw = self._sampler._llm.draw_sample(formatted_prompt)

            resp_pythoncode = re.findall(r'```python(.*)```', resp_txt_raw, flags=re.DOTALL)
            resp_pythoncode = (['pass']+resp_pythoncode)[-1]
            resp_codepreface = re.findall(r'^(.*)\ndef ', resp_pythoncode, flags=re.DOTALL)
            resp_codepreface = (['']+resp_codepreface)[-1]
            resp_txt_trim = SampleTrimmer.auto_trim(resp_pythoncode)
            prog = SampleTrimmer.sample_to_program(resp_txt_trim, self._problem_spec.template)

            if not self._is_solution:
                evaluation = None
            elif prog is None:
                evaluation = Evaluation(fitness=float("inf"), errors="no program found")
            else:
                prog = Program(preface=resp_codepreface, functions=prog.functions)
                evaluation = self._problem_spec.evaluator(
                    [ff for ff in prog.exec() if ff.__name__ == self._problem_spec.entrypoint][0]
                )
            artifact: Artifact = (
                self._artifact_class(
                    response=resp_txt_raw,
                    program=prog,
                    id=next(self._engine._id_generator)
                )
                .set_evaluation(evaluation)
            )

            if self._engine.tracing:
                self._engine._register_trace(
                    input_arts=[inp for inp in list(args)+list(kwargs.values()) if isinstance(inp, Artifact)],
                    output_art=artifact,
                    prompt_builder_name=prompt_builder_func.__name__
                )
            return artifact
        return _sampling_func


class _TmpApiSpecContext:
    def __init__(self, engine):
        self._engine = engine
        self._new_sampler = None
        self._old_sampler = None
    
    def __call__(self, api_spec):
        if api_spec is not None:
            self._new_sampler = SampleTrimmer(HttpsApi(**api_spec))
        return self

    def __enter__(self):
        if self._new_sampler is not None:
            self._old_sampler = self._engine._sampler
            self._old_cnt = self._engine._id_generator
            self._engine._sampler = self._new_sampler
            self._engine._id_generator = itertools.count()
    
    def __exit__(self, type, value, traceback):
        if self._new_sampler is not None:
            self._engine._sampler = self._old_sampler
            self._engine._id_generator = self._old_cnt


class _TmpProblemSpecContext:
    def __init__(self, engine):
        self._engine = engine
        self._new_spec = None
        self._old_spec = None
    
    def __call__(self, problem_spec):
        self._new_spec = problem_spec
        return self

    def __enter__(self):
        if self._new_spec is not None:
            self._old_spec = self._engine._problem_spec
            self._old_cnt = self._engine._id_generator
            self._engine._problem_spec = self._new_spec
            self._engine._id_generator = itertools.count()
    
    def __exit__(self, type, value, traceback):
        if self._new_spec is not None:
            self._engine._problem_spec = self._old_spec
            self._engine._id_generator = self._old_cnt


class LLMSolutionEngine:
    def __init__(self, api_spec=None, problem_spec=None, debug=False, tracing=False):
        if api_spec is None:
            self._sampler = None
        else:
            self._sampler = SampleTrimmer(HttpsApi(**api_spec))
        self._problem_spec = problem_spec
        self.prompt_to_artifact = _PromptToArtifactConverter(self, debug=debug)
        self.prompt_to_solution = self.prompt_to_artifact.as_solution()
        self.prompt_to_reflection = self.prompt_to_artifact.as_reflection()
        self.set_api = _TmpApiSpecContext(self)
        self.set_problem = _TmpProblemSpecContext(self)
        self._id_generator = itertools.count()

        self.tracing=tracing
        self.trace_graph = None
        self.trace_list = None
        self.trace_lock = Lock()
    
    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def start_trace(self):
        self.tracing=True
        self.trace_graph = nx.DiGraph()
        self.trace_list = []
        return self
    
    def _register_trace(self, input_arts, output_art, prompt_builder_name=''):
        with self.trace_lock:
            self.trace_list.append(output_art)
            self.trace_graph.add_node(output_art.trace_id, label=f'{prompt_builder_name}-{output_art.trace_id}')
            for inp_art in input_arts:
                self.trace_graph.add_edge(inp_art.trace_id, output_art.trace_id)
        
    def dump_trace(self):
        self.tracing=False
        tracegraph = self.trace_graph
        tracelist = self.trace_list
        self.trace_graph = None
        self.trace_list = None
        return tracegraph, tracelist
    
