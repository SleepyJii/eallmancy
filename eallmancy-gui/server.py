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

from datetime import datetime
from collections import defaultdict
import networkx as nx
import numpy as np


app = FastAPI()

app.state.config = None
app.state.config_updated_timestamp = datetime.utcnow().timestamp()
app.state.eallmancer = Eallmancer()


# Serve React static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")



## CONFIG STUFF

_ALGOS = ["EOH_git"]

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
    }

def _add_graph_positioning(gr):
    components = list()
    for cgraph_nodes in nx.weakly_connected_components(gr):
        cgraph = gr.subgraph(cgraph_nodes)
        
        for node in cgraph.nodes:
            gr.nodes[node]['Yrank'] = np.nan

        longest_path = nx.dag_longest_path(cgraph)
        for nidx, nn in enumerate(longest_path):
            gr.nodes[nn]['Yrank'] = nidx

        for node in cgraph.nodes:
            if gr.nodes[node]['Yrank'] is not np.nan:
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
    js = dict(id = stringify_artid(art.trace_id), type=str(type(art)))
    if art.evaluation is not None:
        js['evaluation'] = str(art.evaluation)
    if hasattr(art, 'solution_part_strs'):
        js['solution_parts'] = art.solution_part_strs
    js['position'] = {'x_rank': ndd['Xrank'], 'y_rank': ndd['Yrank']}
    return js

def _jsonify_edge(edg):
    source, target = edg
    return {'source': stringify_artid(source), 'target': stringify_artid(target)}

@app.get("/api/view/trace")
def get_trace():
    if not app.state.eallmancer.has_trace:
        return { # default empty trace
            "timestamp": datetime.utcnow().timestamp(),
            "graph": {"nodes": [], "edges": []},
        }
    
    trace: EngineTrace = app.state.eallmancer.get_trace()
    enh_graph = _add_graph_positioning(trace.graph)

    # we need to parse the trace as GUI-friendly JSON
    _nodes = [_jsonify_art(ndd) for _, ndd in enh_graph.nodes(data=True)]
    _edges = [_jsonify_edge(edg) for edg in enh_graph.edges]
    
    return {
        "timestamp": datetime.utcnow().timestamp(),
        "graph": {"nodes": _nodes, "edges": _edges},
    }



@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_catchall(full_path: str):
    with open("frontend/build/index.html") as f:
        return f.read()


