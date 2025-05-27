# websocket_manager.py

from typing import Dict, Optional
from fastapi import WebSocket
from uuid import uuid4


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client_id = str(uuid4())
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_to(self, client_id: Optional[str], message: dict):
        if client_id is None:
            # grab active
            ws = None
            for _, ws in self.active_connections.items():
                break
        else:
            ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

