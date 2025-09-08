
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact

from eallmancy import SinglePartSolution, ProblemSpec
import os
import re
import numpy as np
import math
from typing import List
from threading import Lock, Thread


OPENAI_API_SPEC = dict(
        host="api.openai.com",
        key=os.environ.get('OPENAI_API_KEY', ''),
        model="gpt-4o-mini",
        timeout=20
)    

engine = EngineV3(
    api_spec=OPENAI_API_SPEC,
    problem_spec=None
)

class ThoughtfulSolution(SinglePartSolution):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = (re.findall(r'<<(.*)>>', response) or [None])[-1]


    def __str__(self):
        parstr = Artifact.__str__(self)
        header_str, eval_str = parstr.split('\n')
        return f"""
{header_str}

{self.thought}

```python
{'\n'.join(self.solution_part_strs)}
```
{eval_str}
"""
       
# prompt_to_thoughtful_solution = engine.prompt_to_solution.artifact(ThoughtfulSolution)

def i1_solution():
    prmpt = f'''{engine._problem_spec.description}
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>. 
2. Next, implement the following Python function:
{engine._problem_spec.template}
Enclose within a code block like ```python ... ```. Do not give additional explanations.'''
    return engine.generate_artifact(prmpt, ThoughtfulSolution)

def e1_solution(*parent_solns):
    prmpt = f'''{engine._problem_spec.description}
I have {len(parent_solns)} existing algorithms with their codes as follows:
{'\n'.join([f'Solution num {i}:\n{ss.program}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new algorithm that has a totally different form from the given ones. 
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
{engine._problem_spec.template}
Enclose within a code block like ```python ... ```. Do not give additional explanations.'''
    return engine.generate_artifact(prmpt, ThoughtfulSolution, parents=parent_solns)

def e2_solution(*parent_solns):
    prmpt = f'''{engine._problem_spec.description}
I have {len(parent_solns)} existing algorithms with their codes as follows:
{'\n'.join([f'Solution num {i}:\n{ss.program}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new algorithm that has a totally different form from the given ones but can be motivated from them.
1. Firstly, identify the common backbone idea in the provided algorithms. 
2. Secondly, based on the backbone idea describe your new algorithm in one sentence. The description must be inside within boxed <<>>.
3. Thirdly, implement the following Python function:
{engine._problem_spec.template}
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''
    return engine.generate_artifact(prmpt, ThoughtfulSolution, parents=parent_solns)

def m1_solution(parent_soln):
    prmpt = f'''{engine._problem_spec.description}
I have one algorithm with its code as follows. Algorithm description:
{parent_soln.thought}
Code:
{str(parent_soln.program)}
Please assist me in creating a new algorithm that has a different form but can be a modified version of the algorithm provided.
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
{engine._problem_spec.template}
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''
    return engine.generate_artifact(prmpt, ThoughtfulSolution, parents=[parent_soln])

def m2_solution(parent_soln):
    prmpt = f'''{engine._problem_spec.description}
I have one algorithm with its code as follows. Algorithm description:
{parent_soln.thought}
Code:
{str(parent_soln.program)}
Please identify the main algorithm parameters and assist me in creating a new algorithm that has a different parameter settings of the score function provided.
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, implement the following Python function:
{engine._problem_spec.template}
Enclosed within a code block like ```python ... ```. Do not give additional explanations.'''
    return engine.generate_artifact(prmpt, ThoughtfulSolution, parents=[parent_soln])


class Population:
    def __init__(self, init_members=[], popsize=10, max_samples=100, max_generations=100):
        self.members: List[SinglePartSolution] = init_members
        self.popsize = popsize
        self.lock = Lock()
        self.max_samples, self.max_generations = max_samples, max_generations
        self.n_samples, self.n_generations = len(self.members), 0
    
    def selection(self, k):
        with self.lock:
            funcs = [f for f in self.members if not math.isinf(f.evaluation.fitness)]
            if funcs == []:
                return [np.random.choice(self.members) for _ in range(k)]
            else:
                func = sorted(funcs, key=lambda f: f.evaluation.fitness, reverse=engine._problem_spec.maximization)
                p = np.array([1 / (r + len(func)) for r in range(len(func))])
                p /= np.sum(p)
                return [np.random.choice(func, p=p) for _ in range(k)]

    def survival_filter(self):
            self.members = sorted(self.members, key=lambda f: f.evaluation.fitness, reverse=engine._problem_spec.maximization)[:self.popsize]
    
    def register(self, solns):
        with self.lock:
            for soln in solns:
                self.members.append(soln)
                self.n_samples += 1
    
    def eoh_completed(self):
        with self.lock:
            return self.n_samples > self.max_samples or self.n_generations > self.max_generations


def _eoh_worker(population: Population, e1_per_gen=1 ,e2_per_gen=1, m1_per_gen=1, m2_per_gen=1, num_e1_parents=2, num_e2_parents=2, **kwargs):
    while not population.eoh_completed():
        for _ in range(e1_per_gen):
            population.register([e1_solution(*population.selection(num_e1_parents))])
        for _ in range(e2_per_gen):
            population.register([e2_solution(*population.selection(num_e2_parents))])
        for _ in range(m1_per_gen):
            population.register([m1_solution(*population.selection(1))])
        for _ in range(m2_per_gen):
            population.register([m2_solution(*population.selection(1))])

        population.n_generations += 1
        population.survival_filter()


def eoh(initial_size=5, pop_size=5, max_samples=10, max_generations=1e9, problem_spec: ProblemSpec=None, api_spec=OPENAI_API_SPEC, n_workers=1, **kwargs):

    with engine.set(problem_spec=problem_spec, api_spec=api_spec) as ec: 
        engine.start()

        population = Population(
            [i1_solution() for _ in range(initial_size)],
            max_generations=max_generations,
            max_samples=max_samples,
            popsize=pop_size,
        )
        sampler_threads = [
            Thread(target=_eoh_worker, args=(population,), kwargs=kwargs)
            for _ in range(n_workers)
        ]
        for t in sampler_threads:
            t.start()
        for t in sampler_threads:
            t.join()

        return ec.trace


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

