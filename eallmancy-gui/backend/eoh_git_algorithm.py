

from eallmancy.engine.engine_trace import EngineTrace

import re
from eallmancy import MultiPartSolution, DiffSolution, ProblemSpec
from eallmancy import Artifact
from eallmancy.artifacts.multi_part_solutions import DummyMultiPartSolution
from eallmancy.engine.llm_solution_engine_v3 import EngineV3
from backend.eallm_state import SharedState


import numpy as np
import math
from typing import List
from threading import Lock, Thread
import time
import asyncio


# EOH_git artifacts

class ThoughtfulDiffSolution(DiffSolution):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = (re.findall(r'<<(.*)>>', response) or [None])[-1]

    def __str__(self):
        parstr = Artifact.__str__(self)
        header_str, eval_str = parstr.split('\n')
        return f"""
Algorithm: {self.thought}
{'\n\n'.join([f'```\n{x}\n```' for x in self.solution_part_strs])}
{eval_str}
"""

class ThoughtfulSolution(MultiPartSolution):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = (re.findall(r'<<(.*)>>', response) or [None])[-1]

    def __str__(self):
        parstr = Artifact.__str__(self)
        header_str, eval_str = parstr.split('\n')
        return f"""
Algorithm: {self.thought}
{'\n\n'.join([f'```\n{x}\n```' for x in self.solution_part_strs])}
{eval_str}
"""


# EOH_git operations

async def i1_solution(engine: EngineV3):
    prmpt = f'''{engine._problem_spec.description}
1. First, describe your new algorithm and main steps in one sentence. The description must be inside within boxed <<>>. 
2. Next, improve on the following sections of code:
{'\n\n'.join([f'```\n{x}\n```' for x in engine._problem_spec.section_templates])}
Provide your improvements as a FIND-REPLACE block like \n<<<<<<<< SEARCH\ncode_to_find\n========\ncode_to_replace\n>>>>>>>> REPLACE\n
Remember to include appropriate indentations in both SEARCH and REPLACE blocks. Do not give additional explanations.'''
    return await engine.async_generate_artifact(prmpt, ThoughtfulDiffSolution)


async def e1_solution(engine: EngineV3, *parent_solns):
    prmpt = f'''{engine._problem_spec.description}
I have {len(parent_solns)} existing solutions with their contents as follows:
{'\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new solution that is totally different from the given ones. 
1. First, describe your new solution and its contents in one sentence. The description must be inside within boxed <<>>.
2. Next, improve on the following sections of code:
{'\n\n'.join([f'```\n{x}\n```' for x in engine._problem_spec.section_templates])}
Provide your implementation in matching code blocks, each marked like ``` ... ```. Do not give additional explanations.'''
    return await engine.async_generate_artifact(prmpt, ThoughtfulSolution, parents=parent_solns)


async def e2_solution(engine: EngineV3, *parent_solns):
    prmpt = f'''{engine._problem_spec.description}
I have {len(parent_solns)} existing solutions with their contents as follows:
{'\n'.join([f'Solution num {i}:\n{ss}\n' for i, ss in enumerate(parent_solns)])}
Please help me create a new solution that is totally different from the given ones but can be motivated from them.
1. Firstly, identify the common backbone idea in the provided solutions. 
2. Secondly, based on the backbone idea describe your new solution in one sentence. The description must be inside within boxed <<>>.
3. Thirdly, improve on the following sections of code:
{'\n\n'.join([f'```\n{x}\n```' for x in engine._problem_spec.section_templates])}
Provide your implementation in matching code blocks, each marked like ``` ... ```. Do not give additional explanations.'''
    return await engine.async_generate_artifact(prmpt, ThoughtfulSolution, parents=parent_solns)


async def m1_solution(engine: EngineV3, parent_soln):
    prmpt = f'''{engine._problem_spec.description}
I have one solution with its content as follows...
{str(parent_soln)}
Please assist me in creating a new solution that is different but can be a modified version of the solution provided.
1. First, describe your new solution and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, improve on the following sections of code:
{'\n\n'.join([f'```\n{x}\n```' for x in engine._problem_spec.section_templates])}
Provide your improvements as a FIND-REPLACE block like \n<<<<<<<< SEARCH\ncode_to_find\n========\ncode_to_replace\n>>>>>>>> REPLACE\n
Remember to include appropriate indentations in both SEARCH and REPLACE blocks. Do not give additional explanations.'''
    return await engine.async_generate_artifact(prmpt, ThoughtfulDiffSolution, parents=[parent_soln])


async def m2_solution(engine: EngineV3, parent_soln):
    prmpt = f'''{engine._problem_spec.description}
I have one solution with its code as follows...
{str(parent_soln)}
Please identify the main solution parameters and assist me in creating a new solution that has a different parameter settings of the score function provided.
1. First, describe your new solution and main steps in one sentence. The description must be inside within boxed <<>>.
2. Next, improve on the following sections of code:
{'\n\n'.join([f'```\n{x}\n```' for x in engine._problem_spec.section_templates])}
Provide your improvements as a FIND-REPLACE block like \n<<<<<<<< SEARCH\ncode_to_find\n========\ncode_to_replace\n>>>>>>>> REPLACE\n
Remember to include appropriate indentations in both SEARCH and REPLACE blocks. Do not give additional explanations.'''
    return await engine.async_generate_artifact(prmpt, ThoughtfulDiffSolution, parents=[parent_soln])




class Population:
    def __init__(self, init_members=[], popsize=10, max_samples=100, max_generations=100, maximization=True):
        self.members: List[ThoughtfulDiffSolution] = init_members
        self.popsize = popsize
        self.lock = Lock()
        self.max_samples, self.max_generations = max_samples, max_generations
        self.n_samples, self.n_generations = len(self.members), 0
        self.maximization = True
    
    def selection(self, k):
        with self.lock:
            funcs = [f for f in self.members if not math.isinf(f.evaluation.fitness)]
            if funcs == []:
                return [np.random.choice(self.members) for _ in range(k)]
            else:
                func = sorted(funcs, key=lambda f: f.evaluation.fitness, reverse=self.maximization)
                p = np.array([1 / (r + len(func)) for r in range(len(func))])
                p /= np.sum(p)
                return [np.random.choice(func, p=p) for _ in range(k)]

    def survival_filter(self):
            self.members = sorted(self.members, key=lambda f: f.evaluation.fitness, reverse=self.maximization)[:self.popsize]
    
    def register(self, solns):
        with self.lock:
            for soln in solns:
                self.members.append(soln)
                self.n_samples += 1
                if len(self.members) > self.popsize:
                    self.survival_filter()
                    self.n_generations += 1
    
    def eoh_completed(self):
        with self.lock:
            return self.n_samples > self.max_samples or self.n_generations > self.max_generations



# it is assumed we are gonna be running these async.


class EohGitAlgorithm:
    def __init__(self, ps, api, registry_callback, shared_state: SharedState):
                
        self.engine = (
            EngineV3(
                api_spec=None,
                problem_spec=None
            )
            .add_hook(registry_callback)
        )
        self.api = api
        self.ps = ps

        self.num_initial_samples=3
        self.pop_size=5
        self.max_samples=10
        self.max_generations=10
        self._shared_state: SharedState = shared_state

    async def stateful_run_generate(self, operator, *args, **kwargs):

        while (await self._shared_state.get('is_paused')) and not (await self._shared_state.get('kill_signal')):
            await asyncio.sleep(1)

        if await self._shared_state.get('kill_signal'):
            raise Exception("kill signal recieved")
        
        # not paused and no kill signal, CONTINUE
        return await operator(self.engine, *args, **kwargs)

    async def run(self):

        with self.engine.set(problem_spec=self.ps, api_spec=self.api) as ec: 

            init_samples = []
            for _ in range(self.num_initial_samples):
                na = await self.stateful_run_generate(i1_solution)
                init_samples.append(na)
            population = Population(
                init_samples,
                max_generations=self.max_generations,
                max_samples=self.max_samples,
                popsize=self.pop_size,
                maximization=self.ps.maximization
            )
            e1_per_gen=1
            e2_per_gen=1
            m1_per_gen=1
            m2_per_gen=1
            num_e1_parents=2
            num_e2_parents=2
            print('init_solutions',init_samples)

            while not population.eoh_completed():
                for _ in range(e1_per_gen):
                    parent_selection = population.selection(num_e1_parents)
                    print('pop_selection_E1')
                    na = await self.stateful_run_generate(e1_solution, *parent_selection)
                    population.register([na])
                for _ in range(e2_per_gen):
                    parent_selection = population.selection(num_e2_parents)
                    na = await self.stateful_run_generate(e2_solution, *parent_selection)
                    population.register([na])
                for _ in range(m1_per_gen):
                    parent_selection = population.selection(1)
                    na = await self.stateful_run_generate(m1_solution, *parent_selection)
                    population.register([na])
                for _ in range(m2_per_gen):
                    parent_selection = population.selection(1)
                    na = await self.stateful_run_generate(m2_solution, *parent_selection)
                    population.register([na])

        return min(population.members, key=lambda f: f.fitness), ec.trace


