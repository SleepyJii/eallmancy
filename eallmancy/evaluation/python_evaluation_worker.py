
import tempfile
import shutil
import subprocess
from pathlib import Path
import uuid
import math
import os
import re
from eallmancy.sampling import SampleTrimmer, TextFunctionProgramConverter, Program, Function
from abc import ABC, abstractmethod
from typing import List
from eallmancy.evaluation.evaluation import Evaluation
from eallmancy.artifacts.multi_part_solutions import MultiPartSolution, DummyMultiPartSolution, DiffSolution
from eallmancy.engine.evolve_git_spec import ProblemSpec, EvolveGitSpec              

from eallmancy.evaluation.git_disk_utils import (
    find_git_root, get_git_ignored_paths, copy_git_repo_excluding_ignored,
    TmpCheckoutContext, find_evolve_marked_files, find_evolve_marked_sections,
    replace_evolve_marked_sections
)
from eallmancy.evaluation.evaluation_worker import EvaluateSolutionWorker
from wrapt_timeout_decorator import timeout



class PythonEvaluationWorker(EvaluateSolutionWorker):
    def __init__(self, ps: ProblemSpec, idx=0):
        self.problem_spec: ProblemSpec = ps
    
    def _evaluate_program(self, prog, codepreface):
        if prog is None:
            raise Exception("no program found in response")
        else:
            prog = Program(preface=codepreface, functions=prog.functions)
            heuristic = [ff for ff in prog.exec() if ff.__name__ == self.problem_spec.entrypoint][0]
            res = self.problem_spec.evaluator(heuristic)
            
            if type(res) is Evaluation:  # some fitness functions may handle evaluation manually
                if math.isinf(res.fitness):
                    raise Exception(res.errors or 'evaluation returned unbounded value')
                else:
                    return res.fitness
            else:
                if res is None:
                    raise Exception("function returned None instead of a fitness score")
                return res


    def evaluate_solution(self, soln: MultiPartSolution) -> Evaluation:

        if type(soln) is DiffSolution and soln.parent is None:
            soln.set_parent(DummyMultiPartSolution(self.problem_spec.template))
            resp_txt_raw = '\n\n'.join(soln.solution_part_strs)
            soln.set_parent(None)
        else:
            resp_txt_raw = '\n\n'.join(soln.solution_part_strs)

        resp_pythoncode = (['pass']+[resp_txt_raw])[-1]
        resp_codepreface = re.findall(r'^(.*)\ndef ', resp_pythoncode, flags=re.DOTALL)
        resp_codepreface = (['']+resp_codepreface)[-1]
        try:
            resp_txt_trim = SampleTrimmer.auto_trim(resp_pythoncode)
            prog = SampleTrimmer.sample_to_program(resp_txt_trim, self.problem_spec.template)

            eval_func = timeout(self.problem_spec.eval_timeout, timeout_exception=Exception)(self._evaluate_program)
            res = eval_func(prog, resp_codepreface)
            
            return Evaluation(
                fitness = res,
                errors = None
            )
        except Exception as e:
            return Evaluation(
                fitness = float('inf') * (-1 if self.problem_spec.maximization else 1),
                errors = str(e)
            )
        
        # if prog is None:
        #     return Evaluation(fitness=float("inf") * (-1 if self.problem_spec.maximization else 1), errors="no program found")
        # else:
        #     try:
        #         prog = Program(preface=resp_codepreface, functions=prog.functions)
        #         heuristic = [ff for ff in prog.exec() if ff.__name__ == self.problem_spec.entrypoint][0]
        #         res = self.problem_spec.evaluator(heuristic)
                
        #         if type(res) is Evaluation:
        #             return res  # some fitness functions may handle evaluation manually
        #         else:
        #             if res is None:
        #                 raise Exception("function returned None instead of a fitness score")

        #         return Evaluation(
        #             fitness = res,
        #             errors = None
        #         )
        #     except Exception as e:
        #         return Evaluation(
        #             fitness = float('inf') * (-1 if self.problem_spec.maximization else 1),
        #             errors = str(e)
        #         )
