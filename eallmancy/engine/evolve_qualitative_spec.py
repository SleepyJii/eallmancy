
from dataclasses import dataclass
from pathlib import Path
from typing import List
from eallmancy.sampling import SampleTrimmer, TextFunctionProgramConverter, Program, Function
from eallmancy.engine.problem_spec import ProblemSpec

import re

# @dataclasses.dataclass
# class ProblemSpec:
#     description: str    # sentence explaining the goal
#     template: str       # function signature template for LLM to implement
#     entrypoint: str     # name of the function in signature to be evaluated/used directly
#     evaluator: callable # function that accepts solution as callable and returns fitness score
#     maximization: bool = False



@dataclass
class EvolveQualitativeSpec(ProblemSpec):


    def __init__(self, description:str, evaluation_prompts, combination_method, llm_api, maximization: bool = False):
        self.description = description
        self.evaluation_prompts = evaluation_prompts # itll be a list of [{name: vocab, description: give number between 0 and 100...}]
        self.combination_method = combination_method # itll be a string like SUM, MIN, MAX
        self.llm = SampleTrimmer(HttpsApi(**llm_api))._llm
        self.maximization = maximization

    @property
    def entrypoint(self) -> str:
        # no actual entrypoint in unstructured output...
        return ''

    @property
    def template(self) -> str:
        # not actually used in this case! no absolutely required form...
        return 'PLACEHOLDER ANSWER'
    
    @property
    def section_templates(self) -> List[str]:
        return [self.template]

    @property
    def evaluator(self) -> callable:
        # pregenerated in the QualitativeEvaluationWorker
        return lambda : 0
    

