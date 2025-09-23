#!/bin/bash

""":"

THISFILE=$(realpath $0)
cd /root/eallmancy/eallmancy_gui
./rebuild.sh && exec /root/reallm/venv/bin/python3 $THISFILE
exit 1
" """




#!/root/reallm/venv/bin/python3

from eallmancy_gui.gui_handler import GUIHandler
from eallmancy.analysis.engine_trace import EngineTrace
from eallmancy.analysis.analysis_cache import AnalysisCache
from threading import Lock

# trace = EngineTrace.load('/root/data/trace_vault/meta_fs/20250902-144744_7d5e_funs_cvrp_aco-n150-sg20-4ominitmp100.pk')
#trace = EngineTrace.load('/root/data/trace_vault/elmcy_reevo/20250803-013958_8849_reevo_tsp_aco.pk')


class CodeT5PAnalysis:
    pass

class OpenAIAnalysis:
    pass


# vault, fn = ("elmcy_reevo", "20250803-013958_8849_reevo_tsp_aco.pk")
# vault,fn = ("divrs_fs", "20250831-004052_984a_funs_cvrp_aco-n150-sg20-4ominitmp100.pk")
vault,fn = ("divrs_fs", "20250831-004021_3d3c_funs_op_aco-n150-sg20-4ominitmp100.pk")
# vault,fn = ("meta_eoh", "20250901-132527_9c68_eoh_op_aco-n150-ps10-4ominitmp100.pk")

ta = AnalysisCache()
ta = ta.load(f'/root/data/cached_segm_analyses/{vault}/{fn}', name="segment")

trace = ta.segment._trace
trace.lock = Lock()
trace.analysis_cache = ta

print(getattr(trace, 'analysis_cache'))
print(getattr(trace, 'analysis_cache').empty)
print(trace.analysis_cache.segment)

class DataWrapper:
    def __init__(self, trace):
        self.trace = trace

    def get(self):
        return self.trace

dataw = DataWrapper(trace)


testhandler = GUIHandler(snapshot=dataw.get)
testhandler.start()

import time

for i in range(1000):
    time.sleep(1)

input('paused..')
