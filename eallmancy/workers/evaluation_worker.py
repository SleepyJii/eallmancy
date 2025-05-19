
import tempfile
import shutil
import subprocess
from pathlib import Path
import uuid
import os
import re
from abc import ABC, abstractmethod
from eallmancy.base.evaluation import Evaluation
from eallmancy.base2.multi_part_solutions import MultiPartSolution, DummyMultiPartSolution, DiffSolution
from eallmancy.base2.problem_specs import ProblemSpec, EvolveGitSpec


class TmpCheckoutContext:
    def __init__(self, source_root, idx=0):
        self.source_root = source_root
        self.tmp_root = None
        self.idx = idx
    
    def __enter__(self):
        self.tmp_root = tempfile.mkdtemp(prefix='eallm_', suffix=f'_w{self.idx}')
        # TODO: *need* to handle git ignore!
        shutil.copytree(self.source_root, self.tmp_root, dirs_exist_ok=True)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        shutil.rmtree(self.tmp_root)
        self.tmp_root = None
        if exception_type is not None:
            raise exception_value.with_traceback(exception_traceback)


class EvaluateSolutionWorker(ABC):
    def __init__(self, ps: ProblemSpec):
        self.problem_spec = ps

    @abstractmethod
    def evaluate_solution(self, soln):
        pass


class PythonEvaluateSolutionWorker(EvaluateSolutionWorker):
    def __init__(self, ps: ProblemSpec):
        self.problem_spec = ps
    
    def evaluate_solution(self, soln):
        return self.problem_spec.evaluator(soln)


class GitEvaluateSolutionWorker(EvaluateSolutionWorker):
    def __init__(self, ps: EvolveGitSpec, idx=0):
        self.problem_spec = ps
        self.source = self.problem_spec.git_path
        self.idx = idx

    def evaluate_solution(self, soln: MultiPartSolution):
        tmpbuilder = TmpCheckoutContext(self.source, idx=self.idx)
        with tmpbuilder:
            files_to_evolve = self._find_evolve_markers(tmpbuilder.tmp_root)
            if len(files_to_evolve) != 1:
                raise Exception("Expected exactly one file with EVOLVE START / EVOLVE END markers")
            evolve_fp = files_to_evolve[0]

            with open(evolve_fp, 'r') as f:
                content = f.read()
            # detect and catalogue how many to-evolve sections there are in the file
            original_part_strs = re.findall(r'# EVOLVE START(.*?)\n# EVOLVE END', content, re.DOTALL)

            # error out if `solution_part_strs` has a different length then # to-evolve sections
            if type(soln) is DiffSolution and soln.parent is None:
                soln.set_parent(DummyMultiPartSolution(original_part_strs))
                soln_part_strs = soln.solution_part_strs
                soln.set_parent(None)
            else:
                soln_part_strs = soln.solution_part_strs
            
            if len(original_part_strs) != len(soln_part_strs):
                raise Exception('Solution did not provide same number of `solution_part_strs` as files evolve sections!')

            # rolled up sequential replacement
            _idx = 0
            new_content = ''
            for olds, news in zip(original_part_strs, soln_part_strs):
                wrapped_olds = f'# EVOLVE START{olds}\n# EVOLVE END'
                wrapped_news = f'# EVOLVE START{news}\n# EVOLVE END'
                olds_st_idx = content.find(wrapped_olds)
                olds_en_idx = olds_st_idx + len(wrapped_olds)
                new_content += content[_idx:olds_en_idx].replace(wrapped_olds,wrapped_news)
                _idx = len(new_content)
            new_content += content[olds_en_idx:]

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
                timeout=20 # 20s
            )
            if proc.returncode != 0:
                # ERRORED OUT
                _errstr = proc.stderr.decode() # TODO: would like to parse more, but whatever
                raise Exception(_errstr)
            else:
                # expecting a delimited list of float eval numbers
                float_vals = [float(x) for x in proc.stdout.decode().replace(' ', '\t').split('\t') if x != '']
                # TODO: support multiple objectives later. for now, assuming a single one
                score = float_vals[0]

        return score

    def _find_evolve_markers(self, fp): 
        # Compile the regex pattern with DOTALL to allow multiline matching
        regex = re.compile(r'# EVOLVE START.*\n# EVOLVE END', re.DOTALL)

        matching_files = []
        for dirpath, dirnames, filenames in os.walk(fp):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if regex.search(content):
                            matching_files.append(filepath)
                            continue
                except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                    # Skip non-text or inaccessible files
                    continue
        return matching_files

