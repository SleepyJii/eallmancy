

## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation


import os
import numpy as np

from eallmancy.engine.llm_solution_engine_v3 import EngineV3

from eallmancy import Artifact, SinglePartSolution, ProblemSpec
from problems.reevo import InformedProblemSpec
from typing import List, Optional
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
engine.kwargs.update({'trace_analysis': True, 'idea_extractor_llm': OPENAI_API_SPEC})



## PROMPT ENG

class CrossoverSolution(SinglePartSolution):
    pass

class EliteSolution(SinglePartSolution):
    pass

class Reflection(Artifact):
    def __init__(self, response: str, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.thought = response
    
    def __str__(self):
        return f"{self.thought}"

class ComparativeReflection(Reflection):
    pass

class LongTermReflection(Reflection):
    pass


# solutionpair_to_reflection = engine.prompt_to_reflection.add_output(observation=r'<<(.*)>>')
# distilled_reflection = engine.prompt_to_reflection.add_output(observation=r'<<(.*)>>')

# @engine.prompt_to_solution
def initial_solution(engine) -> SinglePartSolution:
    if not issubclass(type(engine._problem_spec), InformedProblemSpec):
        raise Exception("benchmark ReEvo algorithm requires `InformedProblemSpec`")

    pmpt = f"""
You are an expert in the domain of optimization heuristics. Your task is to design heuristics that can effectively solve optimization problems.
Your response outputs Python code and nothing else. Format your code as a Python code string: "```python ... ```".

Write a {engine._problem_spec.entrypoint} function for {engine._problem_spec.description}
{engine._problem_spec.func_description}

{engine._problem_spec.template}

Refer to the format of a trivial design above. Be very creative and give `{engine._problem_spec.entrypoint}`. Output code only and enclose your code with Python code block: ```python ... ```.

{engine._problem_spec.external_knowledge}
"""
    return engine.generate_artifact(pmpt, SinglePartSolution)

# @solutionpair_to_reflection
def comparative_reflection(engine, parenta: SinglePartSolution, parentb: SinglePartSolution) -> Reflection:

    if not issubclass(type(engine._problem_spec), InformedProblemSpec):
        raise Exception("benchmark ReEvo algorithm requires `InformedProblemSpec`")

    scorea, scoreb = parenta.fitness, parentb.fitness
    if (scorea > scoreb) ^ (not engine._problem_spec.maximization):
        better_parent, worse_parent = parenta, parentb
    else:
        better_parent, worse_parent = parentb, parenta

    pmpt = f"""
You are an expert in the domain of optimization heuristics. Your task is to design heuristics that can effectively solve optimization problems.

Below are two `{engine._problem_spec.entrypoint}` functions for {engine._problem_spec.description}
{engine._problem_spec.func_description}

You are provided with two code versions below, where the second version performs better than the first one.

[Worse code]
{worse_parent.program}

[Better code]
{better_parent.program}

You respond with some hints for designing better heuristics, based on the two code versions and using less than 20 words.
"""

    return engine.generate_artifact(pmpt, ComparativeReflection, parents=[parenta, parentb])

# @engine.prompt_to_solution
def crossover_solution(engine, parenta: SinglePartSolution, parentb: SinglePartSolution, comp_refl: ComparativeReflection) -> SinglePartSolution:

    if not issubclass(type(engine._problem_spec), InformedProblemSpec):
        raise Exception("benchmark ReEvo algorithm requires `InformedProblemSpec`")
        
    scorea, scoreb = parenta.fitness, parentb.fitness
    if (scorea > scoreb) ^ (not engine._problem_spec.maximization):
        better_parent, worse_parent = parenta, parentb
    else:
        better_parent, worse_parent = parentb, parenta

    pmpt = f"""
You are an expert in the domain of optimization heuristics. Your task is to design heuristics that can effectively solve optimization problems.
Your response outputs Python code and nothing else. Format your code as a Python code string: "```python ... ```".

Write a {engine._problem_spec.entrypoint} function for {engine._problem_spec.description}
{engine._problem_spec.func_description}

[Worse code]
{worse_parent.program}

[Better code]
{better_parent.program}

[Reflection]
{comp_refl.thought}

[Improved code]
Please write an improved function `{engine._problem_spec.entrypoint}`, according to the reflection. Output code only and enclose your code with Python code block: ```python ... ```.

"""

    return engine.generate_artifact(pmpt, CrossoverSolution, parents=[parenta, parentb, comp_refl])

# @distilled_reflection
def longterm_reflection(engine, prev_longterm_refl: LongTermReflection, st_refls: List[ComparativeReflection]) -> LongTermReflection:

    if not issubclass(type(engine._problem_spec), InformedProblemSpec):
        raise Exception("benchmark ReEvo algorithm requires `InformedProblemSpec`")
        
    st_refls_clean = '\n'.join(map(str,st_refls))
    pmpt = f"""
You are an expert in the domain of optimization heuristics. Your task is to design heuristics that can effectively solve optimization problems.

Below is your prior long-term reflection on designing heuristics for {engine._problem_spec.description}
{prev_longterm_refl}

Below are some newly gained insights.
{st_refls_clean}

Write constructive hints for designing better heuristics, based on prior reflections and new insights and using less than 50 words.
"""

    return engine.generate_artifact(pmpt, LongTermReflection, parents=[prev_longterm_refl, *st_refls])

# @engine.prompt_to_solution
def elite_mutated_solution(engine, longterm_refl: LongTermReflection, elite_soln: SinglePartSolution):

    if not issubclass(type(engine._problem_spec), InformedProblemSpec):
        raise Exception("benchmark ReEvo algorithm requires `InformedProblemSpec`")

    pmpt = f"""
You are an expert in the domain of optimization heuristics. Your task is to design heuristics that can effectively solve optimization problems.
Your response outputs Python code and nothing else. Format your code as a Python code string: "```python ... ```".

Write a {engine._problem_spec.entrypoint} function for {engine._problem_spec.description}
{engine._problem_spec.func_description}

[Prior reflection]
{longterm_refl}
{engine._problem_spec.external_knowledge}

[Code]
{elite_soln.program}

[Improved code]
Please write an mutated function `{engine._problem_spec.entrypoint}`, according to the reflection. Output code only and enclose your code with Python code block: ```python ... ```.

"""

    _par = [elite_soln]
    if longterm_refl is not None:
        _par.append(longterm_refl)
    return engine.generate_artifact(pmpt, EliteSolution, parents=_par)
    


## REEVO MAIN LOOP

import random


def reevo(initial_size=30, pop_size=10, max_samples=100, max_generations=int(1e9), crossover_rate=1.0, mutation_rate=0.5, problem_spec=None, api_spec=None, **kwargs):

    n_solns = 0

    with engine.set(problem_spec=problem_spec, api_spec=api_spec) as ec: 
        print("in context... ps is ", type(engine._problem_spec))
        # initial pop generation
        population = [initial_solution(engine) for _ in range(initial_size)]
        n_solns += pop_size
        longterm_refl = None

        for gidx in range(max_generations):

            random.shuffle(population)

            # short term reflection, compare current population solns
            comparative_refls = []
            for idxa in range(0, len(population), 2):
                if idxa+1 >= len(population):
                    break
                comparative_refls.append(comparative_reflection(engine, population[idxa], population[idxa+1]))
                # print('COMPARREFL\n',comparative_refls[-1])
            
            # crossover, using ST reflections and current solns
            crossover_solns = []
            for refl_idx, comparison_refl in enumerate(comparative_refls):
                if np.random.rand() <= crossover_rate:
                    crossover_solns.append(
                        crossover_solution(engine, population[refl_idx*2], population[refl_idx*2+1], comparison_refl)
                    )
                    n_solns += 1
            
            population.extend(crossover_solns)
            
            # long term reflection, distill past and current comparisons
            longterm_refl = longterm_reflection(engine, longterm_refl, comparative_refls)
            # print('LTREFL\n', longterm_refl)

            if np.random.rand() <= mutation_rate:
                # elitist mutation, using new heuristics and LT reflections
                elite_soln = min(population+crossover_solns, key=lambda ss: ss.fitness * (-1+2*engine._problem_spec.maximization))
                elite_mutated_soln = elite_mutated_solution(engine, longterm_refl, elite_soln)
                population.append(elite_mutated_soln)
                n_solns += 1
            # print('ELITEMUT\n',elite_mutated_solns[0])


            ## APPLY YIZHAO FILTER, using distilled distances from trace analysis!!
            filtered_pop = []
            while population != []:
                m_art = population.pop()
                clust = [m_art]
                for c_idx, c_art in enumerate(population):
                    if ec.trace.trace_analysis.distilled_dist(m_art.trace_id, c_art.trace_id) > 0.96:
                        clust.append(c_art)
                clust = list(sorted(clust, key=lambda aart: aart.fitness, reverse=engine._problem_spec.maximization))
                filtered_pop.append(clust[0]) # keep the best
                population = [p for p in population if p not in clust] # exclude dupes
            population = filtered_pop

            # apply pip_size survival filter
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

