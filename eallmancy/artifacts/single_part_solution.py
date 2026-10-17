
from typing import Optional
import re
from eallmancy.sampling import SampleTrimmer, TextFunctionProgramConverter, Program, Function


from eallmancy.evaluation.evaluation import Evaluation
from eallmancy.artifacts.artifact import Artifact
from eallmancy.artifacts.multi_part_solutions import MultiPartSolution

class SinglePartSolution(MultiPartSolution):
    def __init__(self, response: str, **kwargs):
        super().__init__(response, **kwargs)
        self.solution_part_strs = re.findall(r'```[^\n]*\n(.*?)```', response, re.DOTALL)

    @property
    def fitness(self):
        if self.evaluation is None:
            return None
        return self.evaluation.fitness
    
    @property
    def program(self):
        return '\n'.join(self.solution_part_strs)

    @property
    def program_length(self):
        if self.program is None:
            return 0
        return len(str(self.program))

    def __str__(self):
        parstr = super().__str__()
        header_str, eval_str = parstr.split('\n')
        body = '\n'.join(self.solution_part_strs)
        return f"""
{header_str}
```
{body}
```
{eval_str}
"""

