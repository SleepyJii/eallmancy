
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
from eallmancy.engine.problem_specs import ProblemSpec, EvolveGitSpec      

from eallmancy.evaluation.git_disk_utils import (
    find_git_root, get_git_ignored_paths, copy_git_repo_excluding_ignored,
    TmpCheckoutContext, find_evolve_marked_files, find_evolve_marked_sections,
    replace_evolve_marked_sections
)
from eallmancy.evaluation.evaluation_worker import EvaluateSolutionWorker



class GitEvaluationWorker(EvaluateSolutionWorker):
    def __init__(self, ps: EvolveGitSpec, idx=0):
        self.problem_spec = ps
        self.source = self.problem_spec.git_path
        self.idx = idx
        self.tmpbuilder = TmpCheckoutContext(self.source, idx=self.idx)

    def setup(self):
        if not self.tmpbuilder.checked_out:
            print('work tmp dir built')
            self.tmpbuilder.__enter__()

    def __del__(self):
        print('worker death triggered')
        self.tmpbuilder.__exit__(None, None, None)

    def _evaluate_solution(self, soln: MultiPartSolution) -> List[float]:
        tmpbuilder = self.tmpbuilder
        files_to_evolve = find_evolve_marked_files(self.source, relpath=True)
        if len(files_to_evolve) != 1:
            raise Exception("Expected exactly one file with EVOLVE START / EVOLVE END markers")
        evolve_fp = str(Path(tmpbuilder.tmp_root) / str(files_to_evolve[0]))

        with open(evolve_fp, 'r') as f:
            content = f.read()
        # detect and catalogue how many to-evolve sections there are in the file
        original_part_strs: List[str] = find_evolve_marked_sections(content)

        # error out if `solution_part_strs` has a different length then # to-evolve sections
        # if type(soln) is DiffSolution and soln.parent is None:
        #     soln.set_parent(DummyMultiPartSolution(original_part_strs))
        #     soln_part_strs = soln.solution_part_strs
        # else:
        soln_part_strs = soln.solution_part_strs
        
        if len(original_part_strs) != len(soln_part_strs):
            raise Exception('Solution did not provide same number of `solution_part_strs` as files evolve sections!')

        # rolled up sequential replacement
        new_content: str = replace_evolve_marked_sections(content, soln_part_strs)

        with open(evolve_fp, "w") as f:
            f.write(new_content)

        # actually do evaluate! record `res`
        ## copy script to scrambled FN in tmproot
        _tmp_evalscript_pth = os.path.join(tmpbuilder.tmp_root, f"{uuid.uuid4().hex}.sh")
        shutil.copy(self.problem_spec.eval_script_path, _tmp_evalscript_pth)


        ## run the script, grab the output cleanly
        proc = subprocess.run(
            [_tmp_evalscript_pth],
            capture_output=True,
            cwd=tmpbuilder.tmp_root,
            timeout=30, # TODO: how do I want to parameterise this?
        )
        if proc.returncode != 0:
            # ERRORED OUT
            _errstr = proc.stderr.decode() # TODO: would like to parse more, but whatever
            if 'is not defined' in _errstr:
                print(new_content)
            raise Exception(_errstr)
        else:
            # expecting a delimited list of float eval numbers
            _stdo = proc.stdout.decode()
            _stdo_lines = [x for x in _stdo.split('\n') if x!='']
            _final_stdo = _stdo_lines[-1]
            float_vals = [float(x) for x in _final_stdo.replace(' ', '\t').split('\t') if x != '']
            # TODO: support multiple objectives later. for now, assuming a single one
            if len(float_vals) != 1:
                raise Exception(f'eval script gave {float_vals} as final stdout, is it configured correctly?')
            score = float_vals[0]

        return [score]

    def evaluate_solution(self, soln: MultiPartSolution) -> Evaluation:
        try:
            scores = self._evaluate_solution(soln)
            return Evaluation(
                fitness = scores[0], # TODO: handle multi objective
                errors = None
            )
        except Exception  as e:
            return Evaluation(
                fitness = float('inf'),
                errors = str(e)
            )

    def _async_evaluate_solution(self, soln: MultiPartSolution) -> List[float]:
        tmpbuilder = self.tmpbuilder
        files_to_evolve = find_evolve_marked_files(self.source, relpath=True)
        if len(files_to_evolve) != 1:
            raise Exception("Expected exactly one file with EVOLVE START / EVOLVE END markers")
        evolve_fp = str(Path(tmpbuilder.tmp_root) / str(files_to_evolve[0]))

        with open(evolve_fp, 'r') as f:
            content = f.read()
        # detect and catalogue how many to-evolve sections there are in the file
        original_part_strs: List[str] = find_evolve_marked_sections(content)

        soln_part_strs = soln.solution_part_strs
        
        if len(original_part_strs) != len(soln_part_strs):
            raise Exception('Solution did not provide same number of `solution_part_strs` as files evolve sections!')

        # rolled up sequential replacement
        new_content: str = replace_evolve_marked_sections(content, soln_part_strs)

        with open(evolve_fp, "w") as f:
            f.write(new_content)

        # actually do evaluate! record `res`
        ## copy script to scrambled FN in tmproot
        _tmp_evalscript_pth = os.path.join(tmpbuilder.tmp_root, f"{uuid.uuid4().hex}.sh")
        shutil.copy(self.problem_spec.eval_script_path, _tmp_evalscript_pth)


        ## run the script, grab the output cleanly
        proc = subprocess.run(
            [_tmp_evalscript_pth],
            capture_output=True,
            cwd=tmpbuilder.tmp_root,
            timeout=30, # TODO: how do I want to parameterise this?
        )
        if proc.returncode != 0:
            # ERRORED OUT
            _errstr = proc.stderr.decode() # TODO: would like to parse more, but whatever
            if 'is not defined' in _errstr:
                print(new_content)
            raise Exception(_errstr)
        else:
            # expecting a delimited list of float eval numbers
            _stdo = proc.stdout.decode()
            _stdo_lines = [x for x in _stdo.split('\n') if x!='']
            _final_stdo = _stdo_lines[-1]
            float_vals = [float(x) for x in _final_stdo.replace(' ', '\t').split('\t') if x != '']
            # TODO: support multiple objectives later. for now, assuming a single one
            if len(float_vals) != 1:
                raise Exception(f'eval script gave {float_vals} as final stdout, is it configured correctly?')
            score = float_vals[0]

        return [score]
        
    async def async_evaluate_solution(self, soln: MultiPartSolution) -> Evaluation:
        
        try:
            scores = await self._async_evaluate_solution(soln)
            return Evaluation(
                fitness = scores[0], # TODO: handle multi objective
                errors = None
            )
        except Exception  as e:
            return Evaluation(
                fitness = float('inf'),
                errors = str(e)
            )