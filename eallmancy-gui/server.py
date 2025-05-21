# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from fastapi import APIRouter, Path, Body, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from base.config import Config
from eallmancer import Eallmancer
from eallmancy.engine.engine_trace import EngineTrace

app = FastAPI()

app.state.config = None
app.state.eallmancer = Eallmancer()


# Serve React static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_catchall(full_path: str):
    with open("frontend/build/index.html") as f:
        return f.read()


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
    return {"status": "success"}


## CONTROL STUFF

@app.post("/api/control/start_evolve")
def start_evolve():
    if app.state.config is None:
        raise HTTPException(status_code=400, detail={'invalid': 'config is not set'})
    app.state.eallmancer.run(app.state.config)
    return {'status': 'success'}


@app.post("/api/control/stop_evolve")
def stop_evolve():
    if not app.state.is_running:
        raise HTTPException(status_code=400, details={'invalid': 'engine is not running'})
    app.state.eallmancer.stop()
    return {'status': 'success'}


## TRACEVIEW STUFF

@app.get("/api/view/status")
def get_status():
    # TODO: impl
    # do we ahve config?
    # are we running?
    # do we have trace?
    return {'status': 'success'}


@app.get("/api/view/trace")
def get_trace():
    trace: Optional[EngineTrace] = app.state.eallmancer.get_trace()
    if trace is None:
        raise HTTPException(status_code=400, details={'error': 'no trace is available'})
    # TODO: parse trace into useful format
    return {'status': 'success'}


