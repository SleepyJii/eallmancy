

from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact

from eallmancy import SinglePartSolution, ProblemSpec
from typing import List
import os
import re


class ThoughtfulSolution(SinglePartSolution):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        
        self.thought = (re.findall(r'<<(.*)>>', response, re.DOTALL) or [None])[-1]

    def __str__(self):
        parstr = Artifact.__str__(self)
        header_str, eval_str = parstr.split('\n')
        return f"""
{header_str}
Algorithm: {self.thought}
{'\n\n'.join([f'```\n{x}\n```' for x in self.solution_part_strs])}
{eval_str}
"""

