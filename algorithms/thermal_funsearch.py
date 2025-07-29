

## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation

from eallmancy import SinglePartSolution, ProblemSpec
import os
import numpy as np

from eallmancy.engine.llm_solution_engine_v3 import EngineV3

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


## PROMPT SAMPLERS
### decorated string factories. can use PROBLEM_STATEMENT/PROBLEM_TEMPLATE to access problem details from engine

# @engine.prompt_to_solution
def generate_initial():
    base =  f"""
{engine._problem_spec.description}
Implement the following Python function:
```python
{engine._problem_spec.template}
```
Enclose within a code block like ```python ... ```. Do not give additional explanations.
"""
    return engine.generate_artifact(base, SinglePartSolution)




def _smooth_activation_v0(x, eps=1e-3, target0=0.1):
    L = 1.5  # saturation level
    k = np.log(L / eps - 1) / 6  # slope parameter
    # Compute shift to achieve f(0) ~ target0
    shift = np.log(L / target0 - 1) / k
    return L / (1 + np.exp(-k * (x - shift)))


# @engine.prompt_to_solution
def generate_islespawn_thermalfecundity(trace, *isle_examples):
    base = f'''{engine._problem_spec.description}
Previous implementations, from *worst to best*
'''
    base += '\n'.join(list(map(str, sorted(isle_examples, key=lambda sln: sln.fitness-1*(-1+2*engine._problem_spec.maximization), reverse=True))))
    base += f'''
Please assist in writing a next version of the algorithm with the same function signature:
```python
{engine._problem_spec.template}
```
Enclose within a code block like ```python ... ```. Do not give additional explanations.
'''

    # big brain time. calculate discounted temperature based hacky activation
    og_temp = engine._sampler._llm.kwargs.get('temperature', 1.)
    M = avg_parentage_saturation = sum([trace.graph.out_degree(ie.trace_id) for ie in isle_examples]) / len(isle_examples)
    custom_temp = _smooth_activation_v0(M)#*og_temp

    # temperature KWARG should be passed via context manager into the LLM handling
    return engine.generate_artifact(base, SinglePartSolution, parents=isle_examples, temperature=custom_temp)



def activation_v1(x, ctmp, eps=1e-3, xstar=0.9):
    if ctmp == 0:
        return 1.
    elif x >= xstar:
        return 1.

    tmax = 1.5
    L = tmax / max(ctmp, eps)
    
    return L*(1 - x/xstar) + x/xstar


def generate_islespawn_thermalfomo(trace, *isle_examples):
    base = f'''{engine._problem_spec.description}
Previous implementations, from *worst to best*
'''
    base += '\n'.join(list(map(str, sorted(isle_examples, key=lambda sln: sln.fitness-1*(-1+2*engine._problem_spec.maximization), reverse=True))))
    base += f'''
Please assist in writing a next version of the algorithm with the same function signature:
```python
{engine._problem_spec.template}
```
Enclose within a code block like ```python ... ```. Do not give additional explanations.
'''

    # big brain time. calculate discounted temperature based hacky activation
    og_temp = engine._sampler._llm.kwargs.get('temperature', 1.)

    parent_fitnesses = [ie.fitness for ie in isle_examples]
    avg_parent_fitness = sum(parent_fitnesses) / len(isle_examples)
    curr_tidx = max([a.trace_id for a in trace.list])
    prev_solns = [a for a in trace.list[:]]
    _m = 1 if engine._problem_spec.maximization else -1
    M = avg_fit_pct = 1 - (len([a for a in trace.list if a.is_solution and a.fitness*_m > avg_parent_fitness*_m]) / len([a for a in trace.list if a.is_solution]))


    act = activation_v1(M, og_temp)
    custom_temp = act * og_temp
    # print('par_pct', M,'\tact',act,'\ttemp',custom_temp)

    # temperature KWARG should be passed via context manager into the LLM handling
    return engine.generate_artifact(base, SinglePartSolution, parents=isle_examples, temperature=custom_temp)






## MAIN LOOP
### reasons solely about the prompt composition, shouldn't need to think about prompt or LLM details at all

### useful here to know about the Solution class, intended to implement all meaningful interfaces for this flow

from itertools import chain
from collections import defaultdict
from typing import List, Dict
import numpy as np
import scipy


def _softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    """Returns the tempered softmax of 1D finite `logits`."""
    finite_logits = logits[np.isfinite(logits)]
    if len(finite_logits) == 0: # all infinite, returning uniform distr
        rr = np.ones(logits.shape)
        rr = rr / rr.sum()
        return rr
    if not np.issubdtype(finite_logits.dtype, np.floating):
        finite_logits = np.array(finite_logits, dtype=np.float32)

    result = scipy.special.softmax(finite_logits / temperature, axis=-1)
    # Ensure that probabilities sum to 1 to prevent error in `np.random.choice`.
    index = np.argmax(result)
    result[index] = 1 - np.sum(result[0:index]) - np.sum(result[index+1:])
    full_logits = np.zeros(logits.shape)
    full_logits[np.isfinite(logits)] = result
    full_logits[~np.isfinite(logits)] = 0.0
    return full_logits


class FunIsland:
    def __init__(self, funcs_per_prompt=2, selection_temp_init=0.1, selection_temp_period=30000):
        self.funcs_per_prompt = funcs_per_prompt
        self._clusters: Dict[tuple[float, ...], List[SinglePartSolution]] = defaultdict(lambda : [])
        self.selection_temp_init = selection_temp_init
        self.selection_temp_period = selection_temp_period
    
    def register(self, soln):
        self._clusters[(soln.fitness,)].append(soln)
        return self

    def best_soln(self):
        return min(chain(*self._clusters.values()), key=lambda sln: sln.fitness * -1*(-1+2*engine._problem_spec.maximization))

    def select_parents(self):

        # PROBS PER CLUSTER
        cluster_scores = {sign: np.mean(sign) for sign in self._clusters.keys()}
        num_progs = {sign: len(mems) for sign, mems in self._clusters.items()}
        temp_init, temp_period = self.selection_temp_init, self.selection_temp_period
        cluster_probs = _softmax(
            np.array(list(cluster_scores.values())) * (-1+2*engine._problem_spec.maximization), # -1 for minimization 
            temp_init * (1 - sum(list(num_progs.values())) % temp_period) / temp_period
        )

        # PROBS WITHIN CLUSTERS
        cluster_mem_lengths = [
            np.array([sln.program_length for sln in mems])
            for idx, mems in enumerate(self._clusters.values())
        ]
        cluster_mem_probs = [
            _softmax(-1.0 * (lens - lens.min()) / (1e-6 + lens.max()), temperature=1.0)
            for lens in cluster_mem_lengths
        ]

        all_solns = list(chain(*[mems for kv, mems in self._clusters.items()]))
        all_soln_probs = np.concatenate(
            [c_pr * cm_pr for c_pr, cm_pr in zip(cluster_probs, cluster_mem_probs)]
        )
        return np.random.choice(
            all_solns,
            size=min(self.funcs_per_prompt, len(self._clusters)),
            p=all_soln_probs
        )


def thermal_funsearch_v0(n_isles=10, max_samples=2*60, samples_per_generation=30, api_spec=None, problem_spec=None):

    with engine.set(problem_spec=problem_spec, api_spec=api_spec) as ec: 
        engine.start()


        islands = [FunIsland().register(generate_initial()) for _ in range(n_isles)]

        for sidx in range(1,max_samples+1):
            isle_idx = np.random.randint(len(islands))
            new_soln = generate_islespawn_thermalfecundity(engine.trace, *islands[isle_idx].select_parents())
            islands[isle_idx].register(new_soln)

            if (sidx % samples_per_generation) == 0: # reset worst half of the islands
                islands = list(sorted(
                    islands,
                    key=lambda i: i.best_soln().fitness + np.random.random()*1.e-6,
                    reverse=engine._problem_spec.maximization
                ))
                keep_islands = islands[:len(islands) // 2]
                founder_islands = np.random.choice(keep_islands, size=(len(islands) - len(keep_islands)))
                new_islands = [
                    FunIsland().register(origin_isle.best_soln())
                    for origin_isle in founder_islands
                ]
                islands = keep_islands + new_islands

        return ec.trace




def thermal_funsearch_v1(n_isles=10, max_samples=2*60, samples_per_generation=30, api_spec=None, problem_spec=None):

    with engine.set(problem_spec=problem_spec, api_spec=api_spec) as ec: 
        engine.start()


        islands = [FunIsland().register(generate_initial()) for _ in range(n_isles)]

        for sidx in range(1,max_samples+1):
            isle_idx = np.random.randint(len(islands))
            new_soln = generate_islespawn_thermalfomo(engine.trace, *islands[isle_idx].select_parents())
            islands[isle_idx].register(new_soln)

            if (sidx % samples_per_generation) == 0: # reset worst half of the islands
                islands = list(sorted(
                    islands,
                    key=lambda i: i.best_soln().fitness + np.random.random()*1.e-6,
                    reverse=engine._problem_spec.maximization
                ))
                keep_islands = islands[:len(islands) // 2]
                founder_islands = np.random.choice(keep_islands, size=(len(islands) - len(keep_islands)))
                new_islands = [
                    FunIsland().register(origin_isle.best_soln())
                    for origin_isle in founder_islands
                ]
                islands = keep_islands + new_islands

        return ec.trace






if __name__=="__main__":


    ## TOY USE CASE

    import random

    from eallmancy import evaluator
    @evaluator
    def evaluate_pseudorandom(heuristic):
        randseed = random.randint(1,23489)
        return heuristic(randseed)
    
    print('starting FUNSEARCH')

    soln = funsearch(
        n_isles=2,
        max_time=60,
        problem_spec=ProblemSpec(
            description="Generate a random number (integer) from some random seed (int)",
            template="""def random_num(inp: int) -> int:\n\tpass""",
            entrypoint="random_num",
            evaluator=evaluate_pseudorandom
        )
    )

    print(soln)
