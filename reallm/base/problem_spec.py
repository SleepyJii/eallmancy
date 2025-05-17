

import dataclasses


@dataclasses.dataclass
class ProblemSpec:
    description: str    # sentence explaining the goal
    template: str       # function signature template for LLM to implement
    entrypoint: str     # name of the function in signature to be evaluated/used directly
    evaluator: callable # function that accepts solution as callable and returns fitness score

