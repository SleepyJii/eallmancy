

import re
from typing import Dict, List, Optional

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
from reallm.engine_trace import EngineTrace

from threading import Lock, Thread


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

class EngineV2:
    def __init__(self, api_spec=None, problem_spec: ProblemSpec=None, debug=False, tracing=False):
        if api_spec is None:
            self._sampler = None
        else:
            self._sampler = SampleTrimmer(HttpsApi(**api_spec))
        self._problem_spec = problem_spec
        self.set_api = _TmpApiSpecContext(self)
        self.set_problem = _TmpProblemSpecContext(self)
        self._id_generator = itertools.count()

        self.trace: Optional[EngineTrace] = None # EngineTrace()
        # self.tracing=tracing
        # self.trace_graph = None
        # self.trace_list = None
        # self.trace_lock = Lock()
    
    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def start_trace(self):
        # TODO: change this to just instantiate a EngineTrace object
        # self.tracing=True
        # self.trace_graph = nx.DiGraph()
        # self.trace_list = []
        if self.trace is None:
            self.trace = EngineTrace()
        return self
    
    # def _register_trace(self, input_arts, output_art, prompt_builder_name=''):
    #     with self.trace_lock:
    #         self.trace_list.append(output_art)
    #         self.trace_graph.add_node(
    #             output_art.trace_id,
    #             label=f'{prompt_builder_name or "OP"}-{output_art.trace_id}',
    #             artifact=output_art
    #         )
    #         for inp_art in input_arts:
    #             if inp_art is not None:
    #                 self.trace_graph.add_edge(inp_art.trace_id, output_art.trace_id)
        
    def dump_trace(self):
        # TODO: change this to just drop out the EngineTrace object
        # self.tracing=False
        # tracegraph = self.trace_graph
        # tracelist = self.trace_list
        # self.trace_graph = None
        # self.trace_list = None
        tr = self.trace
        self.trace = None
        return tr
    

    def register_artifact(self, arte: Artifact, parents: List[Artifact] = []):
        if self.trace is not None:
            self.trace._register_trace(parents, arte)

        # if self.tracing:
        #     if arte.trace_id is not None:
        #         raise Exception('attempted to register Artifact which already had id {arte.trace_id}')
        #     arte.set_id(next(self._id_generator))
        #     self._register_trace(
        #         input_arts=parents,
        #         output_art=arte,
        #     )


    def generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):

        if not self.is_ready():
            raise Exception(
                "LLMSolutionEngine is not ready! Make sure its supplied with an ApiSpec and ProblemSpec"
            )

        resp_txt_raw = self._sampler._llm.draw_sample(prompt) # TODO: add backoffs

        resp_pythoncode = re.findall(r'```python(.*)```', resp_txt_raw, flags=re.DOTALL)
        resp_pythoncode = (['pass']+resp_pythoncode)[-1]
        resp_codepreface = re.findall(r'^(.*)\ndef ', resp_pythoncode, flags=re.DOTALL)
        resp_codepreface = (['']+resp_codepreface)[-1]
        resp_txt_trim = SampleTrimmer.auto_trim(resp_pythoncode)
        prog = SampleTrimmer.sample_to_program(resp_txt_trim, self._problem_spec.template)

        if not issubclass(arte_class, Solution):
            evaluation = None
        elif prog is None:
            evaluation = Evaluation(fitness=float("inf"), errors="no program found")
        else:
            prog = Program(preface=resp_codepreface, functions=prog.functions)
            evaluation = self._problem_spec.evaluator(
                [ff for ff in prog.exec() if ff.__name__ == self._problem_spec.entrypoint][0]
            )
        artifact: Artifact = (
            arte_class(
                response=resp_txt_raw,
                program=prog,
                id=0 if self.trace is None else self.trace.new_id()
            )
            .set_evaluation(evaluation)
        )

        self.register_artifact(artifact, parents)
        # if self.tracing:
        #     self._register_trace(
        #         input_arts=parents,
        #         output_art=artifact,
        #     )

        return artifact

