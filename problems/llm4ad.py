
# there are more such problems that I am not using right now for whatever reason
# TODO: port across everything just for more optionality

from llm4ad.task.optimization.online_bin_packing import OBPEvaluation
from llm4ad.task.optimization.tsp_construct import TSPEvaluation
from llm4ad.task.optimization.jssp_construct import JSSPEvaluation
from llm4ad.task.optimization.cvrp_construct import CVRPEvaluation
from llm4ad.task.optimization.knapsack_construct import KnapsackEvaluation


from eallmancy import ProblemSpec, evaluator as reallm_evaluator_func


from .converters import _swap_max_min

_id = lambda f: f


class OBPProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = OBPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="priority",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )

class TSPProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = TSPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_node",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )

class JSSPProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = JSSPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="determine_next_operation",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )

class CVRPProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = CVRPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_node",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )

class KnapsackProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = KnapsackEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_item",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )


## MISC problems

from llm4ad.task.machine_learning.car_mountain import CarMountainEvaluation
from llm4ad.task.machine_learning.pendulum import PendulumEvaluation
from llm4ad.task.science_discovery.stresstrain.evaluation import SSEvaluation, MAX_NPARAMS as MAX_SS_PARAMS
from llm4ad.task.science_discovery.bactgrow import BGEvaluation, MAX_NPARAMS as MAX_BG_PARAMS
from llm4ad.task.optimization.admissible_set import ASPEvaluation
from llm4ad.task.optimization.vrptw_construct import VRPTWEvaluation

def _evaluate_program_fix(tt):
    def _func(callable_func: callable):
        return tt.evaluate_program('', callable_func)
    return _func

class CarMountainProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = CarMountainEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="choose_action",
            evaluator=reallm_evaluator_func(_signflips(_evaluate_program_fix(tt)), maximization=maximization),
            maximization=maximization
        )

class PendulumProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = PendulumEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="choose_action",
            evaluator=reallm_evaluator_func(_signflips(_evaluate_program_fix(tt)), maximization=maximization),
            maximization=maximization
        )

class StressTrainProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = SSEvaluation()
        _old_params_descr = "params: Array of numeric constants or parameters to be optimized"
        _new_params_descr = f"params: Array of numeric constants or parameters to be optimized, has size ({MAX_SS_PARAMS},)"

        super().__init__(
            description=tt.task_description,
            template=tt.template_program.replace(_old_params_descr, _new_params_descr),
            entrypoint="equation",
            evaluator=reallm_evaluator_func(_signflips(_evaluate_program_fix(tt)), maximization=maximization),
            maximization=maximization
        )

class BactGrowProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = BGEvaluation()
        _old_params_descr = "params: Array of numeric constants or parameters to be optimized"
        _new_params_descr = f"params: Array of numeric constants or parameters to be optimized, has size ({MAX_BG_PARAMS},)"
        
        super().__init__(
            description=tt.task_description,
            template=tt.template_program.replace(_old_params_descr, _new_params_descr),
            entrypoint="equation",
            evaluator=reallm_evaluator_func(_signflips(_evaluate_program_fix(tt)), maximization=maximization),
            maximization=maximization
        )

class AdmissibleSetProblemSpec(ProblemSpec):
    def __init__(self, maximization=False, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = ASPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="priority",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
            maximization=maximization
        )

class VRPTWProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if maximization else _swap_max_min
        tt = VRPTWEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_node",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
            maximization=maximization
        )



