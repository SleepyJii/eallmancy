# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import sys

sys.path.append('../')

from fastapi import APIRouter, Path, Body, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from base.config import Config
from eallmancer import Eallmancer
from eallmancy.engine.engine_trace import EngineTrace

import signal
import sys
from datetime import datetime
from collections import defaultdict
import networkx as nx
import numpy as np


# TODO: THIS IS ULTRA HACKY, PUT API SETTINGS IN CONTROL PANEL
import os
with open('/root/openai_api_key') as f:
    os.environ['OPENAI_API_KEY'] = f.read().replace('\n','')


app = FastAPI()

_ALGOS = ["EOH_git"]
app.state.config = Config(**{
    'repoPath': '/root/eallmancy',
    'evalScript': '/root/eallmancy/test_gitdiff.py',
    'description': 'The `heuristics` function takes as input a distance matrix, and returns prior indicators of how promising it is to include each edge in a solution. The return is of the same shape as the input.',
    'algorithm': _ALGOS[0],
    'overwrite': True
}) # None
app.state.config_updated_timestamp = datetime.utcnow().timestamp()
app.state.eallmancer = Eallmancer()


# Serve React static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")



def cleanup_on_exit():
    worker = getattr(app.state.eallmancer, "_process", None)
    if worker and worker.is_alive():
        print("Terminating subprocess...")
        worker.terminate()
        worker.join()
        print("Subprocess terminated.")

# On SIGINT or SIGTERM, clean up
def handle_exit_signal(signum, frame):
    print(f"Signal {signum} received, shutting down.")
    cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)





## CONFIG STUFF


@app.get("/api/config/algorithms")
def get_algorithms():
    return _ALGOS


class ValidationRequest(BaseModel):
    value: str

@app.post("/api/config/validate/{field}")
def validate_field(field: str, data: ValidationRequest):
    
    val = data.value.strip()
    
    if field in ["repoPath", "evalScript"]:
        if not Path(val).exists():
            return {"valid": False, "error": "file does not exist"}

    return {"valid": True}


@app.post("/api/config/submit")
def submit_config(config: Config):
    errors = {}

    # verify repo and evalscript paths are valid
    if config.repoPath.strip() == '' or not Path(config.repoPath.strip()).exists():
        errors["repoPath"] = f"`{config.repoPath}` is not a valid directory"
    if config.evalScript.strip() == '' or not Path(config.evalScript.strip()).is_file():
        errors["evalScript"] = f"`{config.evalScript}` is not a valid file"

    # make sure description is not actually empty
    if len(config.description.strip()) == 0:
        errors["description"] = "No description provided"

    # make sure algo is populated
    if config.algorithm not in _ALGOS:
        errors["algorithm"] = f"Unknown algorithm {config.algorithm}"
    
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    
    app.state.config = config
    app.state.config_updated_timestamp = datetime.utcnow().timestamp()
    print("CONFIG SET SUCCESSFULLY:", config)
    return {"status": "success"}


## CONTROL STUFF

@app.post("/api/control/start_evolve")
def start_evolve():
    if app.state.config is None:
        raise HTTPException(status_code=400, detail={'invalid': 'config is not set'})
    print("EALLMancy STARTING")
    app.state.eallmancer.run(app.state.config)
    return {'status': 'success'}


@app.post("/api/control/stop_evolve")
def stop_evolve():
    if not app.state.is_running:
        raise HTTPException(status_code=400, details={'invalid': 'engine is not running'})
    print("EALLMancy STOPPING")
    app.state.eallmancer.stop()
    return {'status': 'success'}





## POLLING ENDPOINTS




@app.get("/api/timestamps")
def get_timestamps():
    _ema_timestamp = app.state.eallmancer.get_trace_timestamp()
    trace_timestamp = _ema_timestamp
    status_timestamp = max(_ema_timestamp, app.state.config_updated_timestamp)
    res = {
        "status": {"timestamp": status_timestamp},
        "trace": {"timestamp": trace_timestamp},
    }
    return res

@app.get("/api/view/status")
def get_status():
    _trace = app.state.eallmancer.get_trace()
    return {
        "timestamp": datetime.utcnow().timestamp(),
        "has_config": app.state.config is not None,
        "is_running": app.state.eallmancer.is_running,
        "has_trace": app.state.eallmancer.has_trace,
        "trace_is_live": app.state.eallmancer.trace_is_live
    }

def _add_graph_positioning(gr):
    components = list()
    for cgraph_nodes in nx.weakly_connected_components(gr):
        cgraph = gr.subgraph(cgraph_nodes)
        
        for node in cgraph.nodes:
            gr.nodes[node]['Yrank'] = -1

        longest_path = nx.dag_longest_path(cgraph)
        for nidx, nn in enumerate(longest_path):
            gr.nodes[nn]['Yrank'] = nidx

        for node in cgraph.nodes:
            if gr.nodes[node]['Yrank'] != -1:
                continue
            for nidx, nn in enumerate(longest_path):
                if nx.has_path(cgraph, nn, node):
                    length = nx.shortest_path_length(cgraph, source=nn, target=node)
                    gr.nodes[node]['Yrank'] = nidx + length
                    break
                elif nx.has_path(cgraph, node, nn):
                    length = nx.shortest_path_length(cgraph, source=node, target=nn)
                    gr.nodes[node]['Yrank'] = nidx - length
                    break
        
    n_r = defaultdict(lambda : 0)
    for nidx, ndd in gr.nodes(data=True):
        gr.nodes[nidx]['Xrank'] = n_r[ndd['Yrank']]
        n_r[ndd['Yrank']] += 1
    return gr

def stringify_artid(idx: int):
    return f'A{idx}'

def _jsonify_art(ndd):
    art = ndd['artifact']
    js = dict(id = stringify_artid(art.trace_id), artifact_type=str(type(art)).replace("<class '", "").replace("'>",""))
    if art.evaluation is not None:
        js['evaluation'] = {'fitness': str(art.evaluation.fitness), 'errors': str(art.evaluation.errors)}
    if hasattr(art, 'solution_part_strs'):
        js['solution_parts'] = art.solution_part_strs
    js['position'] = {'x_rank': ndd['Xrank'], 'y_rank': ndd['Yrank']}
    js['artifact_repr'] = str(art)
    js['raw_response'] = art.raw_resp
    js['raw_prompt'] = art.raw_query
    return js

def _jsonify_edge(edg):
    source, target = edg
    return {'source': stringify_artid(source), 'target': stringify_artid(target)}

@app.get("/api/view/trace")
def get_trace():

    _empty_trace = { # default empty trace
            "timestamp": datetime.utcnow().timestamp(),
            "graph": {"nodes": [], "edges": []},
        }

    # TODO: uncomment after testing
    if not app.state.eallmancer.has_trace:
        return _empty_trace
    
    tracegraph = app.state.eallmancer.get_trace()
    if tracegraph is None:
        return _empty_trace
    
    # trace: EngineTrace = EngineTrace.load('/root/example_trace.pk')

    enh_graph = _add_graph_positioning(tracegraph)

    # we need to parse the trace as GUI-friendly JSON
    _nodes = [_jsonify_art(ndd) for _, ndd in enh_graph.nodes(data=True)]
    _edges = [_jsonify_edge(edg) for edg in enh_graph.edges]
    
    res = {
        "timestamp": datetime.utcnow().timestamp(),
        "graph": {"nodes": _nodes, "edges": _edges},
    }
    return res


# everything else should just open the main landing page
@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_catchall(full_path: str):
    with open("frontend/build/index.html") as f:
        return f.read()


