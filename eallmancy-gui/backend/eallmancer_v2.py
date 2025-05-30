
from typing import Optional
import os
from base.config import Config
from eallmancy.engine.engine_trace import EngineTrace
from backend.eoh_git_algorithm import EohGitAlgorithm
from eallmancy.engine.evolve_git_spec import EvolveGitSpec
from eallmancy.engine.evolve_qualitative_spec import EvolveQualitativeSpec
from datetime import datetime
from backend.eallm_state import SharedState

import asyncio

class Eallmancer:
    def __init__(self, serv_msg_q):
        self.serv_msg_q = serv_msg_q
        self.msg_q = asyncio.Queue()
        
        # precached_trace: EngineTrace = EngineTrace.load('/root/example_trace.pk').graph
        precached_trace: EngineTrace = EngineTrace.load('/root/poetry_example_trace.pk').graph
        # precached_trace = None

        self._shared_state = SharedState(
            is_paused=False,
            is_alive=False,
            trace_timestamp=datetime.utcnow().timestamp(),
            trace=precached_trace,
            kill_signal=False
        )

    @staticmethod
    def _convert_uiconfig(cfg, api_details):
        if cfg['algo_type'] == 'gitdiff':
            return EvolveGitSpec(
                        cfg['description'],
                        cfg['repoPath'],
                        cfg['evalScript'],
                        maximization=True
                    )
        elif cfg['algo_type'] == 'thinkhard':
            return EvolveQualitativeSpec(
                description=cfg['description'],
                evaluation_prompts=cfg['evaluation_prompts'],
                combination_method=cfg['score_combination'],
                llm_api=api_details,
                maximization=False
            )
        else:
            raise Exception(f'cannot create problem spec, unknown algo_type {cfg["algo_type"]}')

    async def run(self, config: Config):
        await self._shared_state.update(
            is_paused=False,
            is_alive=True,
            trace_timestamp=datetime.utcnow().timestamp(),
            trace=None,
            kill_signal=False,
        )
        await self.serv_msg_q.put(dict(type='GET_STATUS', payload=[]))
        await self.serv_msg_q.put(dict(type='GET_TIMESTAMPS', payload=[]))
        try:
            algo_settings = config.get('algo_settings', dict())
            api_details = dict(
                    host="api.openai.com",
                    key=os.environ.get('OPENAI_API_KEY'),
                    model="gpt-4o-mini",
                    timeout=20
                )
            algo = EohGitAlgorithm(
                await asyncio.to_thread(self._convert_uiconfig, config, api_details),
                api_details,
                registry_callback=self.trigger_ui_update,
                shared_state=self._shared_state,
                **algo_settings
            )
            res = await algo.run()
        except Exception as e:
            print("EALLMancy run failed with:",e)
        await self._shared_state.update(
            is_paused=False,
            is_alive=False,
            kill_signal=False
        )
        await self.serv_msg_q.put(dict(type='GET_STATUS', payload=[]))
    
    async def trigger_ui_update(self, latest_trace: EngineTrace):
        # store trace info
        await self._shared_state.update(**{
            'trace_timestamp': datetime.utcnow().timestamp(),
            'trace': latest_trace.graph
            })

        # trigger UI update
        _upd_task = dict(type='GET_TIMESTAMPS', payload=[])
        await self.serv_msg_q.put(_upd_task)
        print(f"\tnew soln in trace")

    async def start(self):
        await self._shared_state.update(**{
            'is_paused': False
        })

    # async def stop(self):
    #     await self._shared_state.update(**{
    #         'is_paused': True
    #     })

    async def kill(self):
        await self._shared_state.update(**{
            'kill_signal': True
        })

    async def get_trace_timestamp(self):
        return await self._shared_state.get('trace_timestamp')

    async def get_trace(self) -> Optional[EngineTrace]:
        return await self._shared_state.get('trace')

    async def is_running(self):
        r1 = await self._shared_state.get('is_alive')
        r2 = await self._shared_state.get('is_paused')
        return r1 and not r2
    
    async def has_trace(self):
        res = await self._shared_state.get('trace')
        return res is not None

    async def trace_is_live(self):
        has_trace = await self.has_trace()
        is_alive = await self._shared_state.get('is_alive')
        return has_trace and is_alive

