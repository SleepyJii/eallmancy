
from dataclasses import dataclass
from pathlib import Path

from eallmancy.engine.problem_spec import ProblemSpec
from eallmancy.evaluation.git_disk_utils import find_evolve_marked_file_sections, find_evolve_marked_files



# @dataclasses.dataclass
# class ProblemSpec:
#     description: str    # sentence explaining the goal
#     template: str       # function signature template for LLM to implement
#     entrypoint: str     # name of the function in signature to be evaluated/used directly
#     evaluator: callable # function that accepts solution as callable and returns fitness score




@dataclass
class EvolveGitSpec(ProblemSpec):

    git_path: str = ''
    eval_script_path: str = ''

    def __init__(self, description:str, git_path:str, eval_script_path:str, maximization: bool = False):
        self.description = description
        self.git_path = git_path
        self.eval_script_path = eval_script_path
        self.maximization = maximization
        
        self._file_to_evolve = None
        self._section_templates = None
        self._template = None
    
    def validate_paths(self):
        if not Path(self.git_path).exists():
            raise Exception(f'`{self.git_path}` does not exist')
        if not Path(self.eval_script_path).exists():
            raise Exception(f'`{self.eval_script_path}` does not exist')
        
    def _resolve(self):
        self.validate_paths()
        _fte = find_evolve_marked_files(self.git_path)
        if len(_fte) == 0:
            raise Exception(f"No file-to-evolve markings found within repo {self.git_path}")
        self._file_to_evolve = _fte[0]
        self._section_templates = find_evolve_marked_file_sections(self._file_to_evolve)
        self._template = '\n\n'.join(self._section_templates)

    @property
    def file_to_evolve(self):
        if self._file_to_evolve is None:
            self._resolve()
        return self._file_to_evolve

    @property
    def section_templates(self):
        if self._section_templates is None:
            self._resolve()
        return self._section_templates
    
    @property
    def template(self):
        if self._template is None:
            self._resolve()
        return self._template

    @property
    def entrypoint(self) -> str:
        # name of the function in signature to be evaluated/used directly
        return ''

    @property
    def evaluator(self) -> callable:
        # function that accepts solution as callable and returns fitness score
        return lambda : 0
    

