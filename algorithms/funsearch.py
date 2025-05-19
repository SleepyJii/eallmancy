

## PROMPT-TO-SOLUTION ENGINE
### uses api information and problem details for easy prompt evaluation

from eallmancy import LLMSolutionEngine, Solution, ProblemSpec
import os


engine = LLMSolutionEngine(
    api_spec=dict(
        host="api.openai.com",
        key=os.environ['OPENAI_API_KEY'],  # your key, e.g., sk-xxxxxxxxxx
        model="gpt-4o-mini",  # your llm, e.g., gpt-3.5-turbo, deepseek-chat
        timeout=20
    ),
    problem_spec=None  # can alternatively specify problem here.
)


## PROMPT SAMPLERS
### decorated string factories. can use PROBLEM_STATEMENT/PROBLEM_TEMPLATE to access problem details from engine

@engine.prompt_to_solution
def generate_initial():
    return """
<PROBLEM_DESCR>
Implement the following Python function:
```python
<PROBLEM_TEMPLATE>
```
Enclose within a code block like ```python ... ```. Do not give additional explanations.
"""

@engine.prompt_to_solution
def generate_islespawn(*isle_examples):
    base = '''<PROBLEM_DESCR>
Previous implementations, from *worst to best*
'''
    base += '\n'.join(list(map(str, sorted(isle_examples, key=lambda sln: sln.fitness, reverse=True))))
    base += '''
Please assist in writing a next version of the algorithm with the same function signature:
<PROBLEM_TEMPLATE>
Enclose within a code block like ```python ... ```. Do not give additional explanations.
'''
    return base



## MAIN LOOP
### reasons solely about the prompt composition, shouldn't need to think about prompt or LLM details at all

### useful here to know about the Solution class, intended to implement all meaningful interfaces for this flow

from itertools import chain
from collections import defaultdict
from typing import List, Dict
import numpy as np
import scipy
import time


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
    return result


class FunIsland:
    def __init__(self, funcs_per_prompt=4, selection_temp_init=0.1, selection_temp_period=30000):
        self.funcs_per_prompt = funcs_per_prompt
        self._clusters: Dict[tuple[float, ...], List[Solution]] = defaultdict(lambda : [])
        self.selection_temp_init = selection_temp_init
        self.selection_temp_period = selection_temp_period
    
    def register(self, soln):
        self._clusters[(soln.fitness,)].append(soln)
        return self

    def best_soln(self):
        return min(chain(*self._clusters.values()), key=lambda sln: sln.fitness)

    def select_parents(self):

        # PROBS PER CLUSTER
        cluster_scores = {sign: np.mean(sign) for sign in self._clusters.keys()}
        num_progs = {sign: len(mems) for sign, mems in self._clusters.items()}
        temp_init, temp_period = self.selection_temp_init, self.selection_temp_period
        cluster_probs = _softmax(
            np.array(list(cluster_scores.values())) * -1, # -1 for minimization 
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


def funsearch(n_isles=10, max_time=2*60, reset_period=4*60*60, api_spec=None, problem_spec=None):

    with engine.set_api(api_spec):
        with engine.set_problem(problem_spec):  
            islands = [FunIsland().register(generate_initial()) for _ in range(n_isles)]

            st_time = time.time()
            while time.time()-st_time < max_time:
                isle_idx = np.random.randint(len(islands))
                new_soln = generate_islespawn(*islands[isle_idx].select_parents())
                islands[isle_idx].register(new_soln)

                last_reset_time = time.time()
                if (time.time() - last_reset_time > reset_period): # reset worst half of the islands
                    islands = list(sorted(
                        islands,
                        key=lambda i: i.best_soln().fitness + np.random.random()*1.e-6
                    ))
                    keep_islands = islands[:len(islands) // 2]
                    founder_islands = np.random.choice(keep_islands, size=(len(islands) - len(keep_islands)))
                    new_islands = [
                        FunIsland().register(origin_isle.best_soln())
                        for origin_isle in founder_islands
                    ]
                    islands = keep_islands + new_islands
                    last_reset_time = time.time()

    return min(islands, key=lambda ii: ii.best_soln().fitness).best_soln()


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
