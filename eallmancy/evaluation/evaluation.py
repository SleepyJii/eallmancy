
from typing import Optional
import dataclasses


@dataclasses.dataclass
class Evaluation:
    fitness: float
    errors: Optional[str] = None
    notes: Optional[str] = ''


def evaluator(func):
    def _func(heuristic):
        try:
            res = func(heuristic)
            return Evaluation(
                fitness = res,
                errors = None
            )
        except Exception as e:
            return Evaluation(
                fitness = float('inf'),
                errors = str(e)
            )
    return _func

