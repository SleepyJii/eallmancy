
from typing import Optional
from base.config import Config
import multiprocessing
from multiprocessing import Lock
from multiprocessing import Manager
import os
from eallmancy.engine.problem_specs import EvolveGitSpec
from algorithms.eoh_git import eoh as eohgit, engine as eohgit_engine
from eallmancy.engine.engine_trace import EngineTrace
from datetime import datetime
import asyncio

# should make this a clean, abstracted, multiproc worker

from eallmancy.artifacts.multi_part_solutions import MultiPartSolution
from eallmancy.evaluation.git_disk_utils import replace_evolve_marked_sections


class LiveTargetUpdater:
    def __init__(self, ps, overwrite, _mancer_shared, _mancer_timestamp, tracelock):
        self._tracelock = tracelock
        self.best_score = float('inf')
        self._shared = _mancer_shared
        self._shared["_latest_trace"] = None
        self._last_timestamp = _mancer_timestamp
        self._last_timestamp.value = datetime.utcnow().timestamp()
        self.overwrite = overwrite
        if self.overwrite:
            self.evolve_fp = ps.file_to_evolve
            with open(self.evolve_fp, 'r') as f:
                self._content = f.read()

    async def inform_new_trace(self):
        await self._shared['serv_msg_q'].put(dict(msg_type='GET_TIMESTAMPS')) 

    def hook(self, latest_trace):
        with self._tracelock:
            self._last_timestamp.value = datetime.utcnow().timestamp()
            self._shared["_latest_trace"] = latest_trace.graph
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.inform_new_trace())
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
    def __init__(self, serv_msg_q):
        self._process = None
        self._is_running = multiprocessing.Value('b', False)
        self._stop_event = multiprocessing.Event()
        self._liveupdater = None

        self._manager = Manager()
        self._shared = self._manager.dict()
        #precached_trace: EngineTrace = EngineTrace.load('/root/example_trace.pk')
        # precached_trace: EngineTrace = EngineTrace.load('/root/poetry_example_trace.pk')
        self._shared["_latest_trace"] = None #precached_trace.graph
        self._shared['serv_msg_q'] = serv_msg_q
        self._tracelock = Lock()
        self._servlock = Lock()
        self._last_timestamp = multiprocessing.Value('d', datetime.utcnow().timestamp())

    def run(self, config: Config):
        with self._servlock:
            if self._is_running.value:
                print('EALLMancer already running something', self._is_running.value)
                return
            self._stop_event.clear()
            self._liveupdater = None
            self._process = multiprocessing.Process(target=self._run_task, args=(config,))
            self._is_running.value = True
            self._process.start()
    
    def stop(self):
        with self._servlock:
            if self._process is not None:
                self._stop_event.set()
                self._process.terminate()
                self._process.join()

            if not self._is_running.value:
                print('EALLMancer isnt running something')
                return
            self._is_running.value = False

    def _run_task(self, config: Config):
        print("DOING EALLMANCY")

        try:
            ps = EvolveGitSpec(
                config.description,
                config.repoPath,
                config.evalScript
            )
            self._liveupdater = LiveTargetUpdater(ps, config.overwrite, self._shared, self._last_timestamp, self._tracelock)

            if config.algorithm == 'EOH_git':
                
                eohgit_engine.hooks = [self._liveupdater.hook]
                res = eohgit(
                    problem_spec=ps,
                    api_spec=dict(
                        host="api.openai.com",
                        key=os.environ.get('OPENAI_API_KEY'),
                        model="gpt-4o-mini",
                        timeout=20
                    ),
                    n_workers=1
                )
            else:
                raise Exception(f"Unknown algorithm {config.algorithm}")
        except Exception as e:
            print(e)
        
        with self._servlock:
            with self._tracelock:  # leave trace in clean state after completion
                if self._liveupdater is not None:
                    self._last_timestamp.value = datetime.utcnow().timestamp()
                    self._liveupdater = None
        self._is_running.value = False

    def get_trace_timestamp(self):
        with self._servlock:
            with self._tracelock:
                return self._last_timestamp.value

    def get_trace(self) -> Optional[EngineTrace]:
        with self._servlock:
            with self._tracelock:
                return self._shared["_latest_trace"]

    @property
    def is_running(self):
        with self._servlock:
            return self._is_running.value > 0
    
    @property
    def has_trace(self):
        with self._servlock:
            with self._tracelock:
                return self._is_running.value or self._shared["_latest_trace"] is not None

    @property
    def trace_is_live(self):
        with self._servlock:
            with self._tracelock:
                return self._is_running.value
