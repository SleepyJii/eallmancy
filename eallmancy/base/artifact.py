

from llm4ad.base.sample import SampleTrimmer
from llm4ad.base.code import TextFunctionProgramConverter, Program, Function
from typing import Optional
import datetime
import re


class Artifact:
    def __init__(self, response: str, id: Optional[int] = None, **kwargs):
        self.trace_id = id
        self.raw_resp = response
        self.timestamp = datetime.datetime.now()
        self.evaluation = None
        self.is_solution = False  # whether or not engine should try and evaluate
    
    def set_id(self, idx):
        self.trace_id = idx
        return self
    
    def set_evaluation(self, evald):
        self.evaluation = evald
        return self
    
    def __str__(self):
        return f"Artifact {self.trace_id}\nEvaluation: {self.evaluation if self.evaluation is not None else 'None'}"





