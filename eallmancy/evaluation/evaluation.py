
from typing import Optional
import dataclasses


@dataclasses.dataclass
class Evaluation:
    fitness: float
    errors: Optional[str] = None
    notes: Optional[str] = ''


def evaluator(func, maximization=False):
    if maximization:
        _mult = -1
    else:
        _mult = 1
    def _func(heuristic):
        try:
            res = func(heuristic)
            return Evaluation(
                fitness = res,
                errors = None
            )
        except Exception as e:
            return Evaluation(
                fitness = float('inf') * _mult,
                errors = str(e)
            )
    return _func

