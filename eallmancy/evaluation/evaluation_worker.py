
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
from eallmancy.engine.evolve_git_spec import ProblemSpec, EvolveGitSpec

                

from eallmancy.evaluation.git_disk_utils import (
    find_git_root, get_git_ignored_paths, copy_git_repo_excluding_ignored,
    TmpCheckoutContext, find_evolve_marked_files, find_evolve_marked_sections,
    replace_evolve_marked_sections
)


class EvaluateSolutionWorker(ABC):
    def __init__(self, ps: ProblemSpec, idx=0):
        self.problem_spec = ps

    @abstractmethod
    def evaluate_solution(self, soln):
        pass

    def setup(self):
        pass
