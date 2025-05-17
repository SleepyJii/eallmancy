
from typing import Optional

from llm4ad.base.code import TextFunctionProgramConverter, Program, Function

from reallm.base.evaluation import Evaluation
from reallm.base.artifact import Artifact


class Solution(Artifact):
    def __init__(self, response: str, program: Optional[Program]=None, **kwargs):
        super().__init__(response, **kwargs)
        self.program = program

    @property
    def fitness(self):
        if self.evaluation is None:
            return None
        return self.evaluation.fitness

    @property
    def program_length(self):
        if self.program is None:
            return 0
        return len(str(self.program))

    def __str__(self):
        parstr = super().__str__()
        header_str, eval_str = parstr.split('\n')
        return f"""
{header_str}
```python
{self.program}
```
{eval_str}
"""

