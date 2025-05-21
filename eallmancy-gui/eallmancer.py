
from typing import Optional
from base.config import Config
import multiprocessing
from multiprocessing import Lock

from eallmancy.engine.problem_specs import EvolveGitSpec
from algorithms.eoh_git import eoh as eohgit, engine as eohgit_engine
from eallmancy.engine.engine_trace import EngineTrace
from datetime import datetime

# should make this a clean, abstracted, multiproc worker

from eallmancy.artifacts.multi_part_solutions import MultiPartSolution
from eallmancy.evaluation.git_disk_utils import replace_evolve_marked_sections


class LiveTargetUpdater:
    def __init__(self, ps, overwrite, tracelock):
        self._tracelock = tracelock
        self.best_score = float('inf')
        self.latest_trace = None
        self.latest_timestamp = datetime.utcnow().timestamp()
        self.overwrite = overwrite
        if self.overwrite:
            self.evolve_fp = ps.file_to_evolve
            with open(self.evolve_fp, 'r') as f:
                self._content = f.read()

    def hook(self, latest_trace):
        with self._tracelock:
            self.latest_timestamp = datetime.utcnow().timestamp()
            self.latest_trace = latest_trace
        new_arte = latest_trace.list[-1]
        if issubclass(type(new_arte), MultiPartSolution):
            if new_arte.fitness < self.best_score:
                self.best_score = new_arte.fitness
                print('NEW BEST SCORE:',self.best_score)
                if self.overwrite:
                    self._content = replace_evolve_marked_sections(self._content, new_arte.solution_part_strs)
                    with open(self.evolve_fp, 'w') as f:
                        f.write(self._content)
            else:
                print('.')



class Eallmancer:
    def __init__(self):
        self._process = None
        self._is_running = multiprocessing.Value('b', False)
        self._stop_event = multiprocessing.Event()
        self._liveupdater = None
        self._last_trace = None
        self._tracelock = Lock()
        self._servlock = Lock()
        self._stale_timestamp = datetime.utcnow().timestamp()

    def run(self, config: Config):
        with self._servlock:
            if self._is_running.value:
                return
            self._stop_event.clear()
            self._liveupdater = None
            self._last_trace = None
            self._process = multiprocessing.Process(target=self._run_task, args=(config,))
            self._is_running.value = True
            self._process.start()
    
    def stop(self):
        with self._servlock:
            if not self._is_running.value:
                return
            self._stop_event.set()
            self._process.join()
            self._is_running.value = False

    def _run_task(self, config: Config):
        print("DOING EALLMANCY")
        if config.algorithm == 'EOH_git':
            ps = EvolveGitSpec(
                config.description,
                config.repoPath,
                config.evalScript
            )
            self._liveupdater = LiveTargetUpdater(ps, config.overwrite)
            eohgit_engine.hooks = [self._liveupdater.hook]
            res = eohgit(
                problem_spec=ps,
                n_workers=1
            )
        else:
            raise Exception(f"Unknown algorithm {config.algorithm}")
        with self._servlock:
            with self._tracelock:  # leave trace in clean state after completion
                self._last_trace = self._liveupdater.latest_trace
                self._stale_timestamp = datetime.utcnow().timestamp()
                self._liveupdater = None

    def get_trace_timestamp(self):
        with self._servlock:
            if self._liveupdater is None:
                return self._stale_timestamp
            with self._tracelock:
                return self._liveupdater.latest_timestamp

    def get_trace(self) -> Optional[EngineTrace]:
        with self._servlock:
            with self._tracelock:
                if self._liveupdater is None:
                    return self._last_trace
                if self._liveupdater.latest_trace is not None:
                    self._last_trace = self._liveupdater.latest_trace.copy()
                return self._last_trace

    @property
    def is_running(self):
        with self._servlock:
            return self._is_running.value > 0
    
    @property
    def has_trace(self):
        with self._servlock:
            with self._tracelock:
                return self._is_running.value or self._last_trace is not None
