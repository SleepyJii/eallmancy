import os
class PathContext:
    def __init__(self, pth): self._pth = pth
    def __enter__(self):
        self._oldpath = os.getcwd()
        os.chdir(self._pth)
    def __exit__(self, *args, **kwargs): os.chdir(self._oldpath)




import os

os.environ['APIHOST'] = 'api.openai.com'
os.environ['APIMODEL'] = 'gpt-4o-mini'
with open('/root/openai_api_key','r') as f:
    os.environ['APIKEY'] = f.read().replace('\n','')


from llm4ad.task.optimization.online_bin_packing import OBPEvaluation
from llm4ad.task.optimization.tsp_construct import TSPEvaluation
from llm4ad.task.optimization.jssp_construct import JSSPEvaluation
from llm4ad.tools.llm.llm_api_https import HttpsApi
from llm4ad.method.funsearch import FunSearch
from llm4ad.tools.profiler import ProfilerBase
import os

from reallm_problems.reevo import TSPACOProblemSpec
from reallm_problems.converters import reallm_to_llm4ad

xx = TSPACOProblemSpec()
xx.template = """
import numpy as np
def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    return distance_matrix
"""
ALL_TASKS = dict(
    TSPACO=reallm_to_llm4ad(xx)
    #OBP=OBPEvaluation(),
    #TSP=TSPEvaluation(),
    #JSSP=JSSPEvaluation()
)





def run_llm4ad_fs(llm4ad_eval, max_sample_nums, num_samplers, num_evaluators, debug_mode=False):

    llm = HttpsApi(host=os.environ['APIHOST'],  # your host endpoint, e.g., 'api.openai.com', 'api.deepseek.com'
                   key=os.environ['APIKEY'],  # your key, e.g., 'sk-abcdefghijklmn'
                   model=os.environ['APIMODEL'],  # your llm, e.g., 'gpt-3.5-turbo'
                   timeout=60)
    print(llm)

    method = FunSearch(llm=llm,
                 profiler=ProfilerBase(log_dir=f'logs/{llm4ad_eval.__class__.__name__}', log_style='complex'),
                 evaluation=llm4ad_eval,
                 max_sample_nums=max_sample_nums,
                 samples_per_prompt=1,
                 num_samplers=num_samplers,
                 num_evaluators=num_evaluators,
                 debug_mode=debug_mode)

    method.run()



n_runthroughs = 10

for _ in range(n_runthroughs):
    for tn, evv in ALL_TASKS.items():
        evv.__class__.__name__ = f'{tn}Evaluator'
        with PathContext('/root/eallm'):
            run_llm4ad_fs(
                evv,
                max_sample_nums=85,
                num_samplers=1,
                num_evaluators=1,
                debug_mode=True
            )

