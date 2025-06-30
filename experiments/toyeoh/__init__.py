## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation

from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from eallmancy import Artifact

from eallmancy import SinglePartSolution, ProblemSpec
import os
import re

import numpy as np
import math
from typing import List
from threading import Lock, Thread


engine = EngineV3(
    api_spec=dict(
        host="api.openai.com",
        key=os.environ['OPENAI_API_KEY'],
        model="gpt-4o-mini",
        timeout=20
    ),
    problem_spec=None
)



class ThoughtfulSolution(SinglePartSolution):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = (re.findall(r'<<(.*)>>', response, re.DOTALL) or [None])[-1]


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
    

class Prompts:
    def __init__(self, engine: EngineV3):
        self.engine = engine

    def i1_solution(self):
        prmpt = f'''{self.engine._problem_spec.description}
    1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>. 
    2. Next, implement the following Python function:
    {self.engine._problem_spec.template}
    Enclose within a code block like ```python ... ```. Do not give additional explanations.'''
        return self.engine.generate_artifact(prmpt, ThoughtfulSolution)




    def e1_solution(self, *parents: List[Artifact]):
        prmpt = f'''{self.engine._problem_spec.description}
    I have {len(parents)} existing solutions with their contents as follows:
    {'\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parents)])}

    Please help me create a new implementation that is inspired by but distinct from the existing solutions.
    Try to improve and innovate on the approaches taken in them that seem successful.

    1. First, describe your new solution and its contents in one concise paragraph boxed in <<>> (paragraph starts with <<, ends with >>).
    2. Next, implement the solution accordingly while following the template below:
    {'\n\n'.join([f'```\n{x}\n```' for x in [self.engine._problem_spec.template]])}

    Provide your implementation with the *same* number of content blocks as the previous solution ({1} blocks).
    Wrap the content blocks of the solution in ``` ... ```, but do not wrap the solution description or anything else. Do not give additional explanations.'''

        return self.engine.generate_artifact(prmpt, ThoughtfulSolution, parents=parents)




import numpy as np
import math
from typing import List
from threading import Lock, Thread



class Population:
    def __init__(self, init_members=[], max_samples=100, max_generations=100, unbiased_selection=False):
        self.members: List[SinglePartSolution] = init_members
        self.lock = Lock()
        self.max_samples, self.max_generations = max_samples, max_generations
        self.n_samples, self.n_generations = len(self.members), 0
        self.unbiased_selection = unbiased_selection
    
    def selection(self, k):
        with self.lock:
            if self.unbiased_selection:
                # ignore fitness if specified, return uniform randomly selected
                return [np.random.choice(self.members) for _ in range(k)]

            
            funcs = [f for f in self.members if not math.isinf(f.evaluation.fitness)]
            if funcs == []:
                return [np.random.choice(self.members) for _ in range(k)]
            else:
                func = sorted(funcs, key=lambda f: f.evaluation.fitness, reverse=True)
                p = np.array([1 / (r + len(func)) for r in range(len(func))])
                p /= np.sum(p)
                return [np.random.choice(func, p=p) for _ in range(k)]

    def register(self, solns):
        with self.lock:
            for soln in solns:
                self.members.append(soln)
                self.n_samples += 1
    
    def eoh_completed(self):
        with self.lock:
            return self.n_samples > self.max_samples or self.n_generations > self.max_generations


def _eoh_worker(population: Population, operator, num_parents=1):
    while not population.eoh_completed():
        population.register([operator(*population.selection(num_parents))])




class ToyEoH:
    def __init__(self, api=None, ps: ProblemSpec=None, max_generations=float('inf'), n_workers=1, config=dict()):
        self.num_initial_samples=config.get('num_initial_samples', 5)
        self.max_samples=config.get('max_samples', 10)
        self.max_generations=max_generations
        self.n_workers=n_workers
        self.api_spec = api
        self.problem_spec = ps
        self.config = config

    async def run(self, **kwargs) -> SinglePartSolution:

        # this syntactical sugar just lets you specify an optional new problemspec to eoh(..)
        # specifying the problem spec in the engine constructor is also sufficient
        with engine.set(api_spec=self.api_spec, problem_spec=self.problem_spec): 
            engine.start()
            prompts = Prompts(engine)
            population = Population(
                [prompts.i1_solution() for _ in range(self.num_initial_samples)],
                max_generations=self.max_generations,
                max_samples=self.max_samples,
                unbiased_selection=self.config.get('unbiased_selection', False)
            )
            sampler_threads = [
                Thread(target=_eoh_worker, args=(population, prompts.e1_solution), kwargs=kwargs)
                for _ in range(self.n_workers)
            ]
            for t in sampler_threads:
                t.start()
            for t in sampler_threads:
                t.join()

            return max(population.members, key=lambda f: f.fitness), engine.dump_trace()
