

from eallmancy.engine.evolve_git_spec import ProblemSpec
from eallmancy.artifacts.multi_part_solutions import MultiPartSolution



class EvaluationWorkerPool:
    def __init__(self, worker_class, ps: ProblemSpec, n_workers=1):
        self._workers = [worker_class(ps, idx=idx) for idx in range(n_workers)]

    def setup(self):
        # run setup scripts for workers
        for w in self._workers:
            w.setup()
        return self

    def evaluate_solution(self, soln: MultiPartSolution):
        # TODO: implement parallelism
        return self._workers[0].evaluate_solution(soln)
