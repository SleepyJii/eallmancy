
import tempfile
import shutil
import subprocess
from pathlib import Path
import uuid
import os
import re
from llm4ad.base.sample import SampleTrimmer
from llm4ad.base.code import Program
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



class PythonEvaluationWorker(EvaluateSolutionWorker):
    def __init__(self, ps: ProblemSpec, idx=0):
        self.problem_spec: ProblemSpec = ps
    
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
        resp_txt_trim = SampleTrimmer.auto_trim(resp_pythoncode)
        prog = SampleTrimmer.sample_to_program(resp_txt_trim, self.problem_spec.template)
        
        if prog is None:
            return Evaluation(fitness=float("inf") * (-1 if self.problem_spec.maximization else 1), errors="no program found")
        else:
            try:
                prog = Program(preface=resp_codepreface, functions=prog.functions)
                heuristic = [ff for ff in prog.exec() if ff.__name__ == self.problem_spec.entrypoint][0]
                res = self.problem_spec.evaluator(heuristic)
                
                if type(res) is Evaluation:
                    return res  # some fitness functions may handle evaluation manually

                return Evaluation(
                    fitness = res,
                    errors = None
                )
            except Exception as e:
                return Evaluation(
                    fitness = float('inf') * (-1 if self.problem_spec.maximization else 1),
                    errors = str(e)
                )
