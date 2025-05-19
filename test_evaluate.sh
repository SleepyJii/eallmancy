#!/root/eallmancy/venv/bin/python

import sys

sys.path.append('/root/eallmancy')



from eallmancy.base.problem_spec import ProblemSpec
from problems.reevo import TSPACOProblemSpec, BPPoffACOProblemSpec, CVRPACOProblemSpec, MKPACOProblemSpec, OPACOProblemSpec

def unwrap_reallm(ps):
    oldeval = ps.evaluator
    def _func(*args, **kwargs):
        res = oldeval(*args, **kwargs)
        if res.errors is not None:
            raise Exception(res.errors)
        else:
            return res.fitness
    ps.evaluator = _func
    return ps

ALL_TASKS = dict(
    # OBP=(OBPEvaluation()),
    # TSP=(TSPEvaluation()),
    # JSSP=(JSSPEvaluation()),
     TSPACO=unwrap_reallm(TSPACOProblemSpec()), # WORKING
     BPPoffACO=unwrap_reallm(BPPoffACOProblemSpec()), # WORKING
     CVRPACO=unwrap_reallm(CVRPACOProblemSpec()), # WORKING
     MKPACO=unwrap_reallm(MKPACOProblemSpec()), # WORKING
     OPACO=unwrap_reallm(OPACOProblemSpec()), # WORKING
)

from eallmancy.testheuristic import heuristic

print(ALL_TASKS['TSPACO'].evaluator(heuristic))






