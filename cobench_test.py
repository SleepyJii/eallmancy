

# from cobench.agents import GreedyRefine, DirectAnswer, FunSearch, AIDE, ChainOfExperts, ReEvo, BestOfN
from cobench.evaluation import Evaluator as cobench_Evaluator, get_data as cobench_get_data
# from evaluation import Evaluator as cobench_Evaluator, get_data as cobench_get_data


# Load data

TASK_LIST = ['Aircraft landing', 'Assignment problem', 'Assortment problem', 'Bin packing - one-dimensional', 'Capacitated warehouse location', 'Common due date scheduling', 'Constrained guillotine cutting', 'Constrained non-guillotine cutting', 'Container loading', 'Container loading with weight restrictions', 'Corporate structuring', 'Crew scheduling', 'Equitable partitioning problem', 'Euclidean Steiner problem', 'Flow shop scheduling', 'Generalised assignment problem', 'Graph colouring', 'Hybrid Reentrant Shop Scheduling', 'Job shop scheduling', 'MIS', 'Multi-Demand Multidimensional Knapsack problem', 'Multidimensional knapsack problem', 'Open shop scheduling', 'Packing unequal circles', 'Packing unequal circles area', 'Packing unequal rectangles and squares', 'Packing unequal rectangles and squares area', 'Resource constrained shortest path', 'Set covering', 'Set partitioning', 'TSP', 'Uncapacitated warehouse location', 'Unconstrained guillotine cutting', 'Vehicle routing: period routing', 'p-median - capacitated', 'p-median - uncapacitated']
TASK_LIST = ['Aircraft landing']


# # Define agent, here we use GreedyRefine
# agent = GreedyRefine(
#     problem_description=data.problem_description,
#     timeout=10,
#     model='openai/o3-mini', # We use LiteLLM to call API
# )

from huggingface_hub import snapshot_download

snapshot_download(
    repo_id='CO-Bench/CO-Bench',
    repo_type='dataset',
    local_dir='data'
)

from algorithms import funsearch, eoh, reevo
from reallm import ProblemSpec, Evaluation
import re

for task in TASK_LIST:
    data = cobench_get_data(task, src_dir='data')

    # Define agent, here we use GreedyRefine
    print(f'---==== TRYING {task} ====---')

    prob_descr, prob_templ = data.problem_description.split('\n\n## Implement in Solve Function\n\n')
    
    evaluator = cobench_Evaluator(data, timeout=10)
    def fitness(func):

        feedback = evaluator.evaluate(func)
        feedback.dev_score, feedback.dev_feedback
        if "Caught Error: " in feedback.dev_feedback:
            all_errs =re.findall(r'^.* -> Caught Error: [^\n]*$', feedback.dev_feedback)
            return Evaluation(
                fitness = float('inf'), # CO-Bench frames as a minimization problem
                errors = str('\n'.join(all_errs))
            )
        else:
            return Evaluation(
                fitness = feedback.dev_score * -1,  # CO-Bench frames as a minimization problem
                errors = None
            )

    res = eoh(
        problem_spec=ProblemSpec(
            description=prob_descr,
            template=prob_templ,
            entrypoint="solve",
            evaluator=fitness
        )
    )
    print(res)

    # # Run for 64 iterations
    # for it in range(64):
    #     code = agent.step()
    #     if code is None:  # agent decides to terminate
    #         break
    #     feedback = evaluator.evaluate(code)  # Run evaluation
    #     agent.feedback(feedback.dev_score, feedback.dev_feedback)  # Use dev set score as feedback

    # # Get the final solution
    # code = agent.finalize()
    # feedback = evaluator.evaluate(code)
    # print(feedback.test_feedback)  # Test set score