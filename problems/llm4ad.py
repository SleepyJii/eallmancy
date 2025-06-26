
# there are more such problems that I am not using right now for whatever reason
# TODO: port across everything just for more optionality

from llm4ad.task.optimization.online_bin_packing import OBPEvaluation
from llm4ad.task.optimization.tsp_construct import TSPEvaluation
from llm4ad.task.optimization.jssp_construct import JSSPEvaluation
from llm4ad.task.optimization.cvrp_construct import CVRPEvaluation
from llm4ad.task.optimization.knapsack_construct import KnapsackEvaluation

from llm4ad.task.science_discovery.bactgrow import BGEvaluation
from llm4ad.task.machine_learning.pendulum import PendulumEvaluation

from eallmancy import ProblemSpec, evaluator as reallm_evaluator_func


from .converters import _swap_max_min

_id = lambda f: f

class BGProblemSpec(ProblemSpec):
    def __init__(self, maximization=True, *args, **kwargs):
        _signflips = _id if not maximization else _swap_max_min
        tt = BGEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="equation",
            evaluator=reallm_evaluator_func(_signflips(tt.evaluate), maximization=maximization),
        )


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


