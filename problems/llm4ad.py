
# there are more such problems that I am not using right now for whatever reason
# TODO: port across everything just for more optionality

from llm4ad.task.optimization.online_bin_packing import OBPEvaluation
from llm4ad.task.optimization.tsp_construct import TSPEvaluation
from llm4ad.task.optimization.jssp_construct import JSSPEvaluation
from llm4ad.task.optimization.cvrp_construct import CVRPEvaluation
from llm4ad.task.optimization.knapsack_construct import KnapsackEvaluation

from reallm import ProblemSpec, evaluator as reallm_evaluator_func


class OBPProblemSpec(ProblemSpec):
    def __init__(self, *args, **kwargs):
        tt = OBPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="priority",
            evaluator=reallm_evaluator_func(tt.evaluate),
        )

class TSPProblemSpec(ProblemSpec):
    def __init__(self, *args, **kwargs):
        tt = TSPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_node",
            evaluator=reallm_evaluator_func(tt.evaluate),
        )

class JSSPProblemSpec(ProblemSpec):
    def __init__(self, *args, **kwargs):
        tt = JSSPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="determine_next_operation",
            evaluator=reallm_evaluator_func(tt.evaluate),
        )

class CVRPProblemSpec(ProblemSpec):
    def __init__(self, *args, **kwargs):
        tt = CVRPEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_node",
            evaluator=reallm_evaluator_func(tt.evaluate),
        )

class KnapsackProblemSpec(ProblemSpec):
    def __init__(self, *args, **kwargs):
        tt = KnapsackEvaluation()
        super().__init__(
            description=tt.task_description,
            template=tt.template_program,
            entrypoint="select_next_item",
            evaluator=reallm_evaluator_func(tt.evaluate),
        )


