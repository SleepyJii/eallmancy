

from llm4ad.base.sample import SampleTrimmer
from llm4ad.base.code import TextFunctionProgramConverter, Program, Function
from typing import Optional
import datetime
import re


class Artifact:
    def __init__(self, response: str, id: Optional[int] = None, **kwargs):
        # self._property_patterns = dict()
        self.trace_id = id
        self.raw_resp = response
        self.timestamp = datetime.datetime.now()
        self.evaluation = None
    
    # def add_property_patterns(self, **kwargs):
    #     self._property_patterns.update(kwargs)
    #     for k, _ in kwargs.items():
    #         setattr(self, k, None)
    #     return self

    # def parse_patterns(self, outp_txt):
    #     for pname, ppattern in self._property_patterns.items():
    #         ptrn_vals = re.findall(ppattern, outp_txt)
    #         setattr(self, pname, (ptrn_vals or [None])[0])
    #     return self
    def set_id(self, idx):
        self.trace_id = idx
        return self
    
    def set_evaluation(self, evald):
        self.evaluation = evald
        return self
    
    def __str__(self):
        return f"Artifact {self.trace_id}\nEvaluation: {self.evaluation if self.evaluation is not None else 'None'}"
        # basestr = ''
        # if len(self._property_patterns) > 0:
        #     basestr += '\n'.join([
        #         f'{k}: {getattr(self, k)}' for k,_ in self._property_patterns.items()
        #     ])
        #     basestr += '\n'
        # return basestr




