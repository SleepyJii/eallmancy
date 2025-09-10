

from reevo.problems.bpp_offline_aco.eval_jk import BPPoffACOEvaluator, promptdetails as BPPoffACO_prompts
from reevo.problems.cvrp_aco.eval_jk import CVRPACOEvaluator, promptdetails as CVRPACO_prompts
from reevo.problems.mkp_aco.eval_jk import MKPACOEvaluator, promptdetails as MKPACO_prompts
from reevo.problems.op_aco.eval_jk import OPACOEvaluator, promptdetails as OPACO_prompts
from reevo.problems.tsp_aco.eval_jk import TSPACOEvaluator, promptdetails as TSPACO_prompts

from eallmancy import ProblemSpec, evaluator as reallm_evaluator_func
from .converters import _swap_max_min
from typing import Optional



import dataclasses


@dataclasses.dataclass
class InformedProblemSpec(ProblemSpec):
    setting_description: str = ""
    func_description: str = ""
    external_knowledge: str = ""


_ID = lambda f: f


class BPPoffACOProblemSpec(InformedProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _ID if not maximization else _swap_max_min
        super().__init__(
            description=BPPoffACO_prompts["description"] + '\n' + BPPoffACO_prompts["func_desc"],
            template=BPPoffACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=(_signflips(BPPoffACOEvaluator(*args, **kwargs).evaluate)),
            maximization=maximization,
            external_knowledge=BPPoffACO_prompts["external_knowledge"],
            setting_description=BPPoffACO_prompts["description"],
            func_description=BPPoffACO_prompts["func_desc"],
        )

class CVRPACOProblemSpec(InformedProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _ID if not maximization else _swap_max_min
        super().__init__(
            description=CVRPACO_prompts["description"] + '\n' + CVRPACO_prompts["func_desc"],
            template=CVRPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=(_signflips(CVRPACOEvaluator(*args, **kwargs).evaluate)),
            maximization=maximization,
            external_knowledge=CVRPACO_prompts["external_knowledge"],
            setting_description=CVRPACO_prompts["description"],
            func_description=CVRPACO_prompts["func_desc"],
        )

class MKPACOProblemSpec(InformedProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _ID if maximization else _swap_max_min
        super().__init__(
            description=MKPACO_prompts["description"] + '\n' + MKPACO_prompts["func_desc"],
            template=MKPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=(_signflips(MKPACOEvaluator(*args, **kwargs).evaluate)),
            maximization=maximization,
            external_knowledge=MKPACO_prompts["external_knowledge"],
            setting_description=MKPACO_prompts["description"],
            func_description=MKPACO_prompts["func_desc"],
        )

class OPACOProblemSpec(InformedProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _ID if maximization else _swap_max_min
        super().__init__(
            description=OPACO_prompts["description"] + '\n' + OPACO_prompts["func_desc"],
            template=OPACO_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=(_signflips(OPACOEvaluator(*args, **kwargs).evaluate)),
            maximization=maximization,
            external_knowledge=OPACO_prompts["external_knowledge"],
            setting_description=OPACO_prompts["description"],
            func_description=OPACO_prompts["func_desc"],
        )

class TSPACOProblemSpec(InformedProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _ID if not maximization else _swap_max_min
        super().__init__(
            description=TSPACO_prompts["description"] + '\n' + TSPACO_prompts["func_desc"],
            template=TSPACO_prompts["seed_func"],
            entrypoint="heuristic",
            evaluator=(_signflips(TSPACOEvaluator(*args, **kwargs).evaluate)),
            maximization=maximization,
            external_knowledge=TSPACO_prompts["external_knowledge"],
            setting_description=TSPACO_prompts["description"],
            func_description=TSPACO_prompts["func_desc"],
        )

