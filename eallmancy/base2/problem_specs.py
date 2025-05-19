
from dataclasses import dataclass
from pathlib import Path

from eallmancy.base.problem_spec import ProblemSpec



# @dataclasses.dataclass
# class ProblemSpec:
#     description: str    # sentence explaining the goal
#     template: str       # function signature template for LLM to implement
#     entrypoint: str     # name of the function in signature to be evaluated/used directly
#     evaluator: callable # function that accepts solution as callable and returns fitness score




@dataclass
class EvolveGitSpec:#(ProblemSpec):

    description: str
    git_path: str
    eval_script_path: str

    # template: str
    # entrypoint: str
    # evaluator: callable

    def __init__(self, description:str, git_path:str, eval_script_path:str):
        self.description = description
        self.git_path = git_path
        self.eval_script_path = eval_script_path

    def validate_paths(self):
        if not Path(self.git_path).exists():
            raise Exception(f'`{self.git_path}` does not exist')
        if not Path(self.eval_script_path).exists():
            raise Exception(f'`{self.eval_script_path}` does not exist')


    # @template.setter
    # def template(self, v: str) -> None:
    #     pass

    @property
    def template(self) -> str:
        # function signature template for LLM to implement
        return ''

    # @entrypoint.setter
    # def entrypoint(self, v: str) -> None:
    #     pass

    @property
    def entrypoint(self) -> str:
        # name of the function in signature to be evaluated/used directly
        return ''

    # @evaluator.setter
    # def evaluator(self, v: callable) -> None:
    #     pass

    @property
    def evaluator(self) -> callable:
        # function that accepts solution as callable and returns fitness score
        return lambda : 0

