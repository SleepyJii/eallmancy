# gui_handler.py

from __future__ import annotations
from typing import Callable, Dict, Any, Optional
import asyncio, threading, socket
from contextlib import closing
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import signal
import datetime

# UGH
from eallmancy_gui.backend.websocket_manager import ConnectionManager
from eallmancy_gui.backend.msg_worker import msg_worker, _get_timestamps
from eallmancy_gui.backend_utils import _add_graph_positioning, _add_fitness_rank, _jsonify_art, _jsonify_edge
from eallmancy_gui.backend_utils import _build_templ_lookup, _jsonify_segm_templ



def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class GUIHandler:
    """
    Jupyter-friendly FastAPI server wrapper. Delegates endpoint logic
    to externally defined callables.
    """

    def __init__(
        self,
        snapshot: Callable[[], Dict[str, Any]],
        *,
        title: str = "Live Trace",
        host: str = "127.0.0.1",
        port: Optional[int] = 42999,
        # external handlers you provide elsewhere
        state_endpoint: Optional[Callable[[], Any]] = None,
        websocket_endpoint: Optional[Callable[[WebSocket, "GUIHandler"], Any]] = None,
    ) -> None:
        self._snapshot = snapshot
        self._title = title
        self._host = host
        self._port = port or _free_port()

        self._state_endpoint = state_endpoint
        self._websocket_endpoint = websocket_endpoint

        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

        # sync/async bridge for notify
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cond: Optional[asyncio.Condition] = None
        self._version: int = 0
        self._vlock = threading.Lock()

    # ---------------- public API ---------------- #

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def start(self) -> str:
        if self._thread and self._thread.is_alive():
            return self.url

        app = self._build_app()
        config = uvicorn.Config(app, host=self._host, port=self._port,
                                log_level="info", lifespan="on")
        self._server = uvicorn.Server(config)

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._cond = asyncio.Condition()
            try:
                loop.run_until_complete(self._server.serve())
            finally:
                self._cond = None
                self._loop = None

        print(f'LAUNCHING ON {self._host}, {self._port}')
        self._thread = threading.Thread(target=_run, name="GUIHandler", daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if self._server and self._server.started and not self._server.should_exit:
            self._server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._server = None
        self._thread = None

    def notify(self) -> None:
        """
        Call after parent state mutation to wake WebSocket listeners.
        """
        with self._vlock:
            self._version += 1
        loop, cond = self._loop, self._cond
        if loop and cond and not loop.is_closed():
            async def _ping():
                async with cond:
                    cond.notify_all()
            asyncio.run_coroutine_threadsafe(_ping(), loop)

    def snapshot(self) -> Dict[str, Any]:
        return self._snapshot()

    def version(self) -> int:
        with self._vlock:
            return self._version

    # ---------------- internals ---------------- #

    def _build_app(self) -> FastAPI:

        fetch_trace = self._snapshot




        def _init_app(app):
            app.state.config = None
            app.state.config_updated_timestamp = datetime.utcnow().timestamp()

            app.state.conn_manager = ConnectionManager()
            app.state.message_queue = asyncio.Queue()
            app.state.worker_tasks = [
                asyncio.create_task(msg_worker(app.state.message_queue, app.state))
                for _ in range(_MSG_WORKERS)
            ]
            # app.state.eallmancer = Eallmancer(app.state.message_queue)


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




        app = FastAPI(title=self._title)
        guiproj_path = (Path(__file__).absolute().parent)
        staticfiles_dir = (guiproj_path / 'frontend' / 'build' / 'static')
        app.mount("/static", StaticFiles(directory=staticfiles_dir.__str__()), name="static")

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        def index():
            with open((guiproj_path / "frontend/build/index.html").__str__()) as f:
                return f.read()


        # @app.websocket("/ws")
        # async def websocket_endpoint(websocket: WebSocket):
        #     _conn_manager = app.state.conn_manager
        #     client_id = await _conn_manager.connect(websocket)

        #     try:
        #         ts = await _get_timestamps(app.state)
        #         await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=ts))
        #         while True:
        #             data = await websocket.receive_json()
        #             data['client_id'] = client_id
        #             await app.state.message_queue.put(data)
                    
        #     except WebSocketDisconnect:
        #         _conn_manager.disconnect(client_id)



        @app.websocket("/ws")
        async def ws(ws: WebSocket, since: Optional[int] = None):
            await ws.accept()

            def build_trace_payload():
                trace = fetch_trace()
                tracegraph = trace.graph
                enh_graph = _add_graph_positioning(tracegraph)
                enh_graph = _add_fitness_rank(enh_graph)

                # we need to parse the trace as GUI-friendly JSON
                _nodes = [_jsonify_art(ndd) for _, ndd in enh_graph.nodes(data=True)]
                _edges = [_jsonify_edge(edg) for edg in enh_graph.edges]

                # analysis constructs
                _pairwise, _segment = (None, None)
                if hasattr(trace, 'analysis_cache') and not getattr(trace, 'analysis_cache').empty:
                    if trace.analysis_cache.is_loaded('segment'):
                        soln_templ_lookup = _build_templ_lookup(trace.analysis_cache.segment.templates)
                        tcmp = trace.analysis_cache.segment._tcmp
                        _segment = {
                            'templates': [_jsonify_segm_templ(templ, tcmp, trace) for templ in trace.analysis_cache.segment.templates],
                            'soln_lookup': soln_templ_lookup,
                        }
                    if trace.analysis_cache.is_loaded('pairwise'):
                        _pairwise = None # TODO
                else:
                    print(' no analysis.')
                    print('\ttrace has it?', hasattr(trace, 'analysis_cache'))
                    if hasattr(trace, 'analysis_cache'):
                        print('\t',trace.analysis_cache.segment)
                        print('\t', trace.analysis_cache.empty)
                
                pl = {
                    "timestamp": datetime.datetime.utcnow().timestamp(),
                    "graph": {"nodes": _nodes, "edges": _edges},
                    "analysis": {"pairwise": _pairwise, "segment": _segment},
                }
                return dict(type='FULL_TRACE_UPDATE', payload=pl)

            try:
                # On connect, send a snapshot if client is behind
                with self._vlock:
                    v = self._version
                if since is None or since < v:
                    await ws.send_json(build_trace_payload())

                # Then wait for notify() signals; also tick every few seconds
                while True:
                    # Wait until notify() fires or a timeout, then send a fresh snapshot
                    if self._cond is None:
                        await asyncio.sleep(1.0)
                    else:
                        async with self._cond:
                            try:
                                await asyncio.wait_for(self._cond.wait(), timeout=2.0)
                            except asyncio.TimeoutError:
                                pass
                    with self._vlock:
                        v = self._version
                    somethingincoming = await ws.receive_text()  # TODO: use this somehow!!!
                    await ws.send_json(build_trace_payload())
            except WebSocketDisconnect:
                return

        return app
