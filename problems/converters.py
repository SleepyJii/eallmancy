
from llm4ad.base import Evaluation as LLM4ADEvaluation

from reallm import ProblemSpec, evaluator as reallm_evaluator_func
import numpy as np
import typing
from typing import Callable, Any, Dict

from abc import ABC, abstractclassmethod
class ReevoEvaluation:
    @abstractclassmethod
    def evaluate(self, heuristic):
        pass

from numbers import Number

def _swap_max_min(obj_f):
    def objective(*args, **kwargs):
        res = obj_f(*args, **kwargs)
        if isinstance(res, Number):
            return res*-1
        return res
    return objective

def llm4ad_to_reallm(ev: LLM4ADEvaluation) -> ProblemSpec:
    x = ev.template_program
    x = x[x.find('def ')+4:]
    entrypoint = x[:x.find('(')] # assuming only one function definition
    return ProblemSpec(
        description=ev.task_description,
        template=ev.template_program,
        entrypoint=entrypoint,
        evaluator=reallm_evaluator_func(_swap_max_min(ev.evaluate)) ## llm4ad evaluate returns float, maximizing
    )

def _unwrap_reallm_evaluator(reallm_eval):
    def evaluate(*args, **kwargs):
        res = reallm_eval(*args, **kwargs)
        if np.isfinite(res.fitness):
            return res.fitness
        else:
            raise Exception(res.errors)
            return None
    return evaluate 

def _lazy_add_np_import(templ_str):
    # llm4ad will often fail if given templates assumping np has been imported.
    if 'np.' in templ_str and 'import numpy as np' not in templ_str:
        return f'import numpy as np\n{templ_str}'
    return templ_str

def reallm_to_llm4ad(ps: ProblemSpec) -> LLM4ADEvaluation:
    _eval = _unwrap_reallm_evaluator(ps.evaluator)
    class _Evaluation(LLM4ADEvaluation):
        def __init__(self):
            super().__init__(
                template_program=_lazy_add_np_import(ps.template),
                task_description=ps.description,
                use_numba_accelerate=False,
                timeout_seconds=300,
            )
        def evaluate_program(self, program_str: str, callable_func: Callable) -> Any | None:
            return self.evaluate(callable_func)
        def evaluate(self, eva: Callable) -> float:
            return _swap_max_min(_eval)(eva)
    return _Evaluation()

#def reevo_to_reallm(ev: ReevoEvaluation, prompts: Dict) -> ProblemSpec:
#    return ProblemSpec(
#  
#)

def reallm_to_reevo(ps: ProblemSpec) -> (ReevoEvaluation, Dict):
    _eval = ps.evaluate
    class _Evaluation(ReevoEvaluation):
        def evaluate(self, heuristic):
            return _eval(heuristic)
    return (
        _Evaluation(),
        dict( # TODO: finish impl
            func_desc='',
            func_signature='',
            external_knowledge='',
            seed_func=''
        )
    )



