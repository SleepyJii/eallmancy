# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import sys

sys.path.append('../')

from fastapi import APIRouter, Path, Body, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from base.config import Config
# from backend.eallmancer import Eallmancer
from backend.eallmancer_v2 import Eallmancer

import signal
import sys
from datetime import datetime
from collections import defaultdict
import networkx as nx
import numpy as np
import asyncio

from backend.websocket_manager import ConnectionManager
from backend.msg_worker import msg_worker, _get_timestamps


# TODO: THIS IS ULTRA HACKY, PUT API SETTINGS IN CONTROL PANEL
import os
with open('/root/openai_api_key') as f:
    os.environ['OPENAI_API_KEY'] = f.read().replace('\n','')

_MSG_WORKERS = 4


def _init_app(app):
    app.state.config = None
    app.state.config_updated_timestamp = datetime.utcnow().timestamp()

    app.state.conn_manager = ConnectionManager()
    app.state.message_queue = asyncio.Queue()
    app.state.worker_tasks = [
        asyncio.create_task(msg_worker(app.state.message_queue, app.state))
        for _ in range(_MSG_WORKERS)
    ]
    app.state.eallmancer = Eallmancer(app.state.message_queue)


def _cleanup_on_exit():
    worker = getattr(app.state.eallmancer, "_process", None)
    if worker and worker.is_alive():
        print("Terminating subprocess...")
        worker.terminate()
        worker.join()
        print("Subprocess terminated.")

# On SIGINT or SIGTERM, clean up
def handle_exit_signal(signum, frame):
    print(f"Signal {signum} received, shutting down.")
    _cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)


app = FastAPI()
_init_app(app)
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")



# everything else should just open the main landing page
@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_catchall(full_path: str):
    with open("frontend/build/index.html") as f:
        return f.read()


# websocket is how we actually pass messages back and forth
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    _conn_manager = app.state.conn_manager
    client_id = await _conn_manager.connect(websocket)

    try:
        ts = await _get_timestamps(app.state)
        await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=ts))
        while True:
            data = await websocket.receive_json()
            data['client_id'] = client_id
            await app.state.message_queue.put(data)
            
    except WebSocketDisconnect:
        _conn_manager.disconnect(client_id)

