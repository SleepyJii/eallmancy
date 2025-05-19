
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
from eallmancy.base.evaluation import Evaluation
from eallmancy.base2.multi_part_solutions import MultiPartSolution, DummyMultiPartSolution, DiffSolution
from eallmancy.base2.problem_specs import ProblemSpec, EvolveGitSpec


def find_git_root(path):
    """Returns the git root directory for a given path, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ['git', '-C', path, 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_git_ignored_paths(git_root):
    """
    Returns a set of all paths (files and directories) excluded by .gitignore.
    """
    try:
        result = subprocess.run(
            ['git', '-C', git_root, 'status', '--ignored', '--porcelain'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        ignored_paths = set()
        for line in result.stdout.splitlines():
            if line.startswith('!! '):
                path = line[3:]
                ignored_paths.add(os.path.join(git_root, path))
        return list(ignored_paths)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get ignored files: {e.stderr}")


def copy_git_repo_excluding_ignored(src_path, dst_path):
    """Copy contents of a Git repo to dst_path, excluding files ignored by .gitignore."""
    git_root = find_git_root(src_path)
    if git_root is None:
        raise ValueError(f"{src_path} is not inside a Git repository.")

    ignored_abs_paths = list(map(Path, get_git_ignored_paths(git_root) + [os.path.join(src_path, '.git')]))

    for root, dirs, files in os.walk(git_root):
        dirs[:] = [d for d in dirs if Path(os.path.join(root, d)) not in ignored_abs_paths]

        rel_root = os.path.relpath(root, git_root)
        dst_dir = os.path.join(dst_path, rel_root)
        os.makedirs(dst_dir, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            if not any([i in Path(src_file).parents for i in ignored_abs_paths]):
                dst_file = os.path.join(dst_dir, file)

                if os.path.islink(src_file):
                    link_target = os.readlink(src_file)
                    os.symlink(link_target, dst_file)
                else:
                    shutil.copy2(src_file, dst_file)
                



class TmpCheckoutContext:
    def __init__(self, source_path, idx=0):
        self.source_root = find_git_root(source_path)
        self.tmp_root = None
        self.idx = idx
    
    def __enter__(self):
        self.tmp_root = tempfile.mkdtemp(prefix='eallm_', suffix=f'_w{self.idx}')
        # TODO: *need* to handle git ignore!
        copy_git_repo_excluding_ignored(self.source_root, self.tmp_root)
        # shutil.copytree(self.source_root, self.tmp_root, dirs_exist_ok=True)

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
            return Evaluation(fitness=float("inf"), errors="no program found")
        else:
            prog = Program(preface=resp_codepreface, functions=prog.functions)
            heuristic = [ff for ff in prog.exec() if ff.__name__ == self.problem_spec.entrypoint][0]
            try:
                res = self.problem_spec.evaluator(heuristic)
                return Evaluation(
                    fitness = res,
                    errors = None
                )
            except Exception as e:
                return Evaluation(
                    fitness = float('inf'),
                    errors = str(e)
                )


class GitEvaluateSolutionWorker(EvaluateSolutionWorker):
    def __init__(self, ps: EvolveGitSpec, idx=0):
        self.problem_spec = ps
        self.source = self.problem_spec.git_path
        self.idx = idx

    def _evaluate_solution(self, soln: MultiPartSolution) -> List[float]:
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
                timeout=30, # TODO: how do I want to parameterise this?
            )
            if proc.returncode != 0:
                # ERRORED OUT
                _errstr = proc.stderr.decode() # TODO: would like to parse more, but whatever
                raise Exception(_errstr)
            else:
                # expecting a delimited list of float eval numbers
                _stdo = proc.stdout.decode()
                _stdo_lines = [x for x in _stdo.split('\n') if x!='']
                print(_stdo_lines)
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
            print(e)
            return Evaluation(
                fitness = float('inf'),
                errors = str(e)
            )
        

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

