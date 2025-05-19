#!/root/reallm/venv/bin/python

from eallmancy.base2.problem_specs import EvolveGitSpec
from eallmancy.base2.multi_part_solutions import DiffSolution
from eallmancy.workers.evaluation_worker import GitEvaluateSolutionWorker



egs = EvolveGitSpec(
description='doesnt matter fker',
git_path='/root/eallmancy',
eval_script_path='/root/eallmancy/test_evaluate.sh',
        )

soln = DiffSolution("""
<<<<<<<< SEARCH
def save
========
def save_yo_mama
>>>>>>>> REPLACE
""")

worker = GitEvaluateSolutionWorker(egs)

res = worker.evaluate_solution(soln)

print(res, type(res))









