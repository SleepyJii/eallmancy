

from reevo.problems.bpp_offline_aco.eval_jk import BPPoffACOEvaluator, promptdetails as BPPoffACO_prompts
from reevo.problems.cvrp_aco.eval_jk import CVRPACOEvaluator, promptdetails as CVRPACO_prompts
from reevo.problems.mkp_aco.eval_jk import MKPACOEvaluator, promptdetails as MKPACO_prompts
from reevo.problems.op_aco.eval_jk import OPACOEvaluator, promptdetails as OPACO_prompts
from reevo.problems.tsp_aco.eval_jk import TSPACOEvaluator, promptdetails as TSPACO_prompts

from eallmancy import ProblemSpec, evaluator as reallm_evaluator_func
from .converters import _swap_max_min


class BPPoffACOProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = id if not maximization else _swap_max_min
        super().__init__(
            description=BPPoffACO_prompts["func_desc"],
            template=BPPoffACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(_signflips(BPPoffACOEvaluator(*args, **kwargs).evaluate)),
        )

class CVRPACOProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = id if not maximization else _swap_max_min
        super().__init__(
            description=CVRPACO_prompts["func_desc"],
            template=CVRPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(_signflips(CVRPACOEvaluator(*args, **kwargs).evaluate)),
        )

class MKPACOProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = id if maximization else _swap_max_min
        super().__init__(
            description=MKPACO_prompts["func_desc"],
            template=MKPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(_signflips(MKPACOEvaluator(*args, **kwargs).evaluate)),
        )

class OPACOProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = id if maximization else _swap_max_min
        super().__init__(
            description=OPACO_prompts["func_desc"],
            template=OPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(_signflips(OPACOEvaluator(*args, **kwargs).evaluate)),
        )

class TSPACOProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = id if not maximization else _swap_max_min
        super().__init__(
            description=TSPACO_prompts["func_desc"],
            template=TSPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(_signflips(TSPACOEvaluator(*args, **kwargs).evaluate)),
        )

