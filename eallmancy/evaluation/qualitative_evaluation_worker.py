
import tempfile
import shutil
import subprocess
from pathlib import Path
import uuid
import os
import re
from eallmancy.sampling import SampleTrimmer, TextFunctionProgramConverter, Program, Function
from abc import ABC, abstractmethod
from typing import List
from eallmancy.evaluation.evaluation import Evaluation
from eallmancy.artifacts.multi_part_solutions import MultiPartSolution, DummyMultiPartSolution, DiffSolution
from eallmancy.engine.evolve_qualitative_spec import EvolveQualitativeSpec
from eallmancy.evaluation.evaluation_worker import EvaluateSolutionWorker



def _wrap_qual_scoring(task_descr, raw_soln, scoring_descr):
    return f"""
Recently a worker was asked to complete the following:
{task_descr}

The worker has come back with result:
{raw_soln}

You are to grade it by the following criterion:
{scoring_descr}

It may be useful to start from a baseline score number, and add or subtract points based on assessments of the contents.
You should be *as strict as possible* while still being fair.
However in the end you should provide *only one final single numeric score*.
When you provide this unique final score, it should be bracketed like <<>>
"""



class QualitativeEvaluationWorker(EvaluateSolutionWorker):
    def __init__(self, ps: EvolveQualitativeSpec, idx=0):
        self.problem_spec = ps

    def _qual_evaluator(self, raw_soln: str) -> float:
        eval_res = dict()
        for eval_dd in self.problem_spec.evaluation_prompts:
            eval_name = eval_dd['name']
            eval_descr = eval_dd['description']

            resp = self.problem_spec.llm.draw_sample(_wrap_qual_scoring(self.problem_spec.description, raw_soln, eval_descr))
            eval_res[eval_name] = int((re.findall(r'<<(.*)>>', resp) or [None])[-1].replace(' ',''))
        
        if self.problem_spec.combination_method == 'SUM':
            final_score = sum(eval_res.values())
        elif self.problem_spec.combination_method == 'MAX':
            final_score = max(eval_res.values())
        elif self.problem_spec.combination_method == 'MIN':
            final_score = min(eval_res.values())
        else:
            raise Exception(f'unknown combination method {self.problem_spec.combination_method}')
        return final_score, f"({', '.join([f'{k}:{v}' for k,v in eval_res.items()])})"

    def evaluate_solution(self, soln: MultiPartSolution) -> Evaluation:

        if type(soln) is DiffSolution and soln.parent is None:
            soln.set_parent(DummyMultiPartSolution(self.problem_spec.template))
            resp_txt_raw = '\n\n'.join(soln.solution_part_strs)
            soln.set_parent(None)
        else:
            resp_txt_raw = '\n\n'.join(soln.solution_part_strs)

        # sometimes the qualitative solutions get confused and generate an answer in multiple parts
        # ..I guess its harmless to do some helpful formatting for them?
        if type(soln) is DiffSolution:
            soln._solution_part_strs = [resp_txt_raw]
        else:
            soln.solution_part_strs = [resp_txt_raw]
        
        try:
            # if len(soln.solution_part_strs) != 1:
            #     raise Exception('Qualitative solution should have len(`solution_part_strs`)==1')
            
            res, notes = self._qual_evaluator(resp_txt_raw)
            return Evaluation(
                fitness = res,
                errors = None,
                notes = notes
            )
        except Exception as e:
            return Evaluation(
                fitness = -1*float('inf') if self.problem_spec.maximization else float('inf'),
                errors = str(e)
            )
