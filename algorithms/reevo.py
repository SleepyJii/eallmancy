

## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation


import os

from eallmancy.engine.llm_solution_engine_v3 import EngineV3

from eallmancy import Artifact, SinglePartSolution, ProblemSpec
from typing import List, Optional
import os
import re


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



## PROMPT ENG

class CrossoverSolution(SinglePartSolution):
    pass

class EliteSolution(SinglePartSolution):
    pass

class Reflection(Artifact):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = (re.findall(r'<<(.*)>>', response) or [None])[-1]
    
    def __str__(self):
        return f"{self.thought}"

class ComparativeReflection(Reflection):
    pass

class LongTermReflection(Reflection):
    pass


# solutionpair_to_reflection = engine.prompt_to_reflection.add_output(observation=r'<<(.*)>>')
# distilled_reflection = engine.prompt_to_reflection.add_output(observation=r'<<(.*)>>')

# @engine.prompt_to_solution
def initial_solution() -> SinglePartSolution:
    pmpt = f"""
Write a `{engine._problem_spec.entrypoint}` function for "{engine._problem_spec.description}"
Be very creative and implement the following Python function:
{engine._problem_spec.template}
Do not give additional explanations, output code only and enclose within a code block like ```python ... ```
"""
    return engine.generate_artifact(pmpt, SinglePartSolution)

# @solutionpair_to_reflection
def comparative_reflection(parenta: SinglePartSolution, parentb: SinglePartSolution) -> Reflection:
    scorea, scoreb = parenta.fitness, parentb.fitness
    if (scorea > scoreb) ^ (not engine._problem_spec.maximization):
        better_parent, worse_parent = parenta, parentb
    else:
        better_parent, worse_parent = parentb, parenta
    pmpt = f"""
Below are two `{engine._problem_spec.entrypoint}` functions for "{engine._problem_spec.description}"\n
You are provided with two code versions below, where the second version performs better than the first one.\n
[Worse code]\n{worse_parent}\n
[Better code]\n{better_parent}\n
You respond with some hints for designing better heuristics, based on the two code versions and using less than 20 words. Your suggestions should *only* pertain to designing the core methodology, do not propose arbitrary data vaildations or quality of life improvements.
*Make sure to bracket your response in <<>>
"""
    return engine.generate_artifact(pmpt, ComparativeReflection, parents=[parenta, parentb])

# @engine.prompt_to_solution
def crossover_solution(parenta: SinglePartSolution, parentb: SinglePartSolution, comp_refl: ComparativeReflection) -> SinglePartSolution:
    scorea, scoreb = parenta.fitness, parentb.fitness
    if (scorea > scoreb) ^ (not engine._problem_spec.maximization):
        better_parent, worse_parent = parenta, parentb
    else:
        better_parent, worse_parent = parentb, parenta
    pmpt = f"""
Write a `{engine._problem_spec.entrypoint}` function for "{engine._problem_spec.description}"\n
[Worse code]\n{worse_parent}\n
[Better code]\n{better_parent}\n
[Reflection]\n{comp_refl}\n
[Improved code]
Please write an improved function `{engine._problem_spec.entrypoint}`, taking into account insights from the reflection.
Make sure your code implements the same function signature as the template below:
```python
{engine._problem_spec.template}
```
Output code only and enclose your code with Python code block: ```python ... ```.
"""
    return engine.generate_artifact(pmpt, CrossoverSolution, parents=[parenta, parentb, comp_refl])

# @distilled_reflection
def longterm_reflection(prev_longterm_refl: LongTermReflection, st_refls: List[ComparativeReflection]) -> LongTermReflection:
    st_refls_clean = '\n'.join(map(str,st_refls))
    pmpt = f"""
Below is your prior long-term reflection on designing heuristics for {engine._problem_spec.description}\n{prev_longterm_refl}\n
Below are some newly gained insights.\n{st_refls_clean}\n
Write constructive hints for designing better heuristics, based on prior reflections and new insights and using less than 50 words.
*Make sure to bracket your constructive response in <<>>
"""
    return engine.generate_artifact(pmpt, LongTermReflection, parents=[prev_longterm_refl, *st_refls])

# @engine.prompt_to_solution
def elite_mutated_solution(longterm_refl: LongTermReflection, elite_soln: SinglePartSolution):
    pmpt = f"""
Write a `{engine._problem_spec.entrypoint}` function for "{engine._problem_spec.description}"\n
[Prior reflection]\n{longterm_refl}\n
[Code]{elite_soln}\n
[Improved code]
Please write a mutated function `{engine._problem_spec.entrypoint}`, taking into account insights from the reflection.
Make sure your code implements the same function signature as the template below:
```python
{engine._problem_spec.template}
```
Output code only and enclose your code with Python code block: ```python ... ```.
"""
    _par = [elite_soln]
    if longterm_refl is not None:
        _par.append(longterm_refl)
    return engine.generate_artifact(pmpt, EliteSolution, parents=_par)
    


## REEVO MAIN LOOP

import random


def reevo(pop_size=8, max_samples=30, max_generations=int(1e9), problem_spec=None, api_spec=None, **kwargs):

    n_solns = 0

    with engine.set(problem_spec=problem_spec, api_spec=api_spec) as ec: 
        engine.start() 
        # initial pop generation
        population = [initial_solution() for _ in range(pop_size)]
        n_solns += pop_size
        longterm_refl = None

        for gidx in range(max_generations):

            random.shuffle(population)

            # short term reflection, compare current population solns
            comparative_refls = []
            for idxa in range(0, len(population), 2):
                if idxa+1 >= len(population):
                    break
                comparative_refls.append(comparative_reflection(population[idxa], population[idxa+1]))
                # print('COMPARREFL\n',comparative_refls[-1])
            
            # crossover, using ST reflections and current solns
            crossover_solns = []
            for refl_idx, comparison_refl in enumerate(comparative_refls):
                crossover_solns.append(
                    crossover_solution(population[refl_idx*2], population[refl_idx*2+1], comparison_refl)
                )
                n_solns += 1
                # print('CROSSOVER\n', crossover_solns[-1])
            
            # long term reflection, distill past and current comparisons
            longterm_refl = longterm_reflection(longterm_refl, comparative_refls)
            # print('LTREFL\n', longterm_refl)

            # elitist mutation, using new heuristics and LT reflections
            elite_soln = min(population+crossover_solns, key=lambda ss: ss.fitness * (-1+2*engine._problem_spec.maximization))
            elite_mutated_solns = [
                elite_mutated_solution(longterm_refl, elite_soln)
                for _ in range(pop_size - len(crossover_solns))
            ]
            n_solns += len(elite_mutated_solns)
            # print('ELITEMUT\n',elite_mutated_solns[0])
            
            population = population + crossover_solns + elite_mutated_solns
            population = list(sorted(population, key=lambda sln: sln.fitness, reverse=engine._problem_spec.maximization))[:pop_size]

            if max_samples < len([art for art in ec.trace.list if art.is_solution]):
                break

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

        
    soln = reevo(
        problem_spec=ProblemSpec(
            description="Generate a random number (integer) from some random seed (int)",
            template="""def random_num(inp: int) -> int:\n\tpass""",
            entrypoint="random_num",
            evaluator=evaluate_pseudorandom
        )
    )

    print(soln)

    # import networkx as nx
    # tgr, tls = engine.dump_trace()
    # print('TRACEGRAPH')
    # nx.write_network_text(tgr)
    # print('collected',len(tls),'solutions')

