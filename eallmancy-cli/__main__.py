import argparse

parser = argparse.ArgumentParser(
    description="run EALLMancy on a git repo with '# EVOLVE' marks"
)
parser.add_argument('--repo', required=True, type=str,
                    help='Repository name or URL.')
parser.add_argument('--evalscript', required=True, type=str,
                    help='Path to the evaluation script.')
parser.add_argument('--descr', required=True, type=str,
                    help='Description of the task.')


parser.add_argument('--algo', type=str, default='EOH', choices=['EOH', 'FS'],
                        help="EA algo to use. Options: ['EOH', 'FS']. Default is 'EOH'")


live_group = parser.add_mutually_exclusive_group()
live_group.add_argument('--enable_overwrite', dest='overwrite', action='store_true',
                        help='Enable live overwrite (default).')
live_group.add_argument('--disable_overwrite', dest='overwrite', action='store_false',
                        help='Disable live overwrite.')
parser.set_defaults(overwrite=True)

args = parser.parse_args()


import os
with open('/root/openai_api_key') as f:
    os.environ['OPENAI_API_KEY'] = f.read().replace('\n','')



from algorithms.eoh_git import eoh, engine
from eallmancy.engine.evolve_git_spec import EvolveGitSpec
from eallmancy.artifacts.multi_part_solutions import MultiPartSolution
from eallmancy.evaluation.git_disk_utils import replace_evolve_marked_sections

ps = EvolveGitSpec(
        description=args.descr,
        git_path=args.repo,
        eval_script_path=args.evalscript
    )

class LiveTargetUpdater:
    def __init__(self, ps, overwrite):
        self.best_score = float('inf')
        self.latest_trace = None
        self.evolve_fp = ps.file_to_evolve
        with open(self.evolve_fp, 'r') as f:
            self._content = f.read()
        self.overwrite = overwrite

    def hook(self, latest_trace):
        self.latest_trace = latest_trace
        new_arte = latest_trace.list[-1]
        if issubclass(type(new_arte), MultiPartSolution):
            print(new_arte)
            if new_arte.fitness < self.best_score:
                self.best_score = new_arte.fitness
                print('=====NEW BEST SCORE=====')

                if self.overwrite:
                    self._content = replace_evolve_marked_sections(self._content, new_arte.solution_part_strs)
                    with open(self.evolve_fp, 'w') as f:
                        f.write(self._content)
                
ltu = LiveTargetUpdater(ps, overwrite=args.overwrite)
engine.add_hook(ltu.hook)


# TODO: add condition handling for `args.algo`
res = eoh(
    problem_spec=ps,
    n_workers=1
)


