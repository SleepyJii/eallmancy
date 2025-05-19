
## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation


from eallmancy import LLMSolutionEngine, Solution, ProblemSpec
import os


engine = LLMSolutionEngine(
    api_spec=dict(
        host="api.openai.com",
        key=os.environ['OPENAI_API_KEY'],
        model="gpt-4o-mini",
        timeout=20
    ),
    problem_spec=None
)

prompt_to_thoughtful_solution = engine.prompt_to_solution.add_output(thought=r'<<(.*)>>')


## PROMPT->SOLUTION OPERATIONS

@prompt_to_thoughtful_solution
def i1_solution():
    return f'''<PROBLEM_DESCR>
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>. 
2. Next, implement the following Python function:
<PROBLEM_TEMPLATE>
Enclose within a code block like ```python ... ```. Do not give additional explanations.'''


@prompt_to_thoughtful_solution
def e1_solution(*parent_solns):
    return f'''<PROBLEM_DESCR>
I have {len(parent_solns)} existing algorithms with their codes as follows:
{'\n'.join([f'Solution num {i}:\n{ss.program}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new algorithm that has a totally different form from the given ones. 
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
<PROBLEM_TEMPLATE>
Enclose within a code block like ```python ... ```. Do not give additional explanations.'''


@prompt_to_thoughtful_solution
def e2_solution(*parent_solns):
    return f'''<PROBLEM_DESCR>
I have {len(parent_solns)} existing algorithms with their codes as follows:
{'\n'.join([f'Solution num {i}:\n{ss.program}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new algorithm that has a totally different form from the given ones but can be motivated from them.
1. Firstly, identify the common backbone idea in the provided algorithms. 
2. Secondly, based on the backbone idea describe your new algorithm in one sentence. The description must be inside within boxed <<>>.
3. Thirdly, implement the following Python function:
<PROBLEM_TEMPLATE>
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''


@prompt_to_thoughtful_solution
def m1_solution(parent_soln):
    return f'''<PROBLEM_DESCR>
I have one algorithm with its code as follows. Algorithm description:
{parent_soln.thought}
Code:
{str(parent_soln.program)}
Please assist me in creating a new algorithm that has a different form but can be a modified version of the algorithm provided.
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
<PROBLEM_TEMPLATE>
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''


@prompt_to_thoughtful_solution
def m2_solution(parent_soln):
    return f'''<PROBLEM_DESCR>
I have one algorithm with its code as follows. Algorithm description:
{parent_soln.thought}
Code:
{str(parent_soln.program)}
Please identify the main algorithm parameters and assist me in creating a new algorithm that has a different parameter settings of the score function provided.
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
<PROBLEM_TEMPLATE>
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''



## EOH MAIN LOOP

import numpy as np
import math
from typing import List


def selection(k, population: List[Solution]):
    funcs = [f for f in population if not math.isinf(f.evaluation.fitness)]
    func = sorted(funcs, key=lambda f: f.evaluation.fitness, reverse=False)
    p = [1 / (r + len(func)) for r in range(len(func))]
    p = np.array(p)
    p = p / np.sum(p)
    if len(p) == 0: # if all solutions failed
        return [np.random.choice(population) for _ in range(k)]
    return [np.random.choice(func, p=p) for _ in range(k)]


def eoh(num_generations=3, num_initial_samples=3, num_e1_parents=2, num_e2_parents=2, e1_per_gen=1 ,e2_per_gen=1, m1_per_gen=1, m2_per_gen=1, problem_spec: ProblemSpec=None) -> Solution:

    # this syntactical sugar just lets you specify an optional new problemspec to eoh(..)
    # specifying the problem spec in the engine constructor is also sufficient
    with engine.set_problem(problem_spec):  

        print(f'Building initial {num_initial_samples} solns..')
        population = [i1_solution() for _ in range(num_initial_samples)]

        for gidx in range(num_generations):
            print(f'\tbuilding generation {gidx}')
            new_e1 = [e1_solution(*selection(num_e1_parents, population)) for _ in range(e1_per_gen)]
            new_e2 = [e2_solution(*selection(num_e2_parents, population)) for _ in range(e2_per_gen)]
            new_m1 = [m1_solution(*selection(1, population)) for _ in range(m1_per_gen)]
            new_m2 = [m2_solution(*selection(1, population)) for _ in range(m2_per_gen)]
            population.extend(new_e1+new_e2+new_m1+new_m2)

        return min(population, key=lambda f: f.fitness)


if __name__=="__main__":
    ## TOY EXAMPLE

    import random

    from eallmancy import Evaluation

    def evaluate_pseudorandom(func):
        randseed = random.randint(1,23489)
        try:
            res = func(randseed)
            return Evaluation(
                fitness = res,
                errors = None
            )
        except Exception as e:
            return Evaluation(
                fitness = float('inf'),
                errors = str(e)
            )


    print('starting EOH')
    soln = eoh(
        problem_spec=ProblemSpec(
            description="Generate a random number (integer) from some random seed (int)",
            template="""def random_num(inp: int) -> int:\n\tpass""",
            entrypoint="random_num",
            evaluator=evaluate_pseudorandom
        )
    )
    print(soln)

