from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from typing import List

from ..services import outbreak_detector, safe_print

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_alerts(self):
        # Fetch real ML anomalies
        try:
            alerts = outbreak_detector.detect_anomalies()
            for connection in self.active_connections:
                try:
                    await connection.send_json({"type": "OUTBREAK_ALERTS", "data": alerts})
                except Exception as e:
                    safe_print(f"Failed to send to websocket: {e}")
        except Exception as e:
            safe_print(f"Anomaly detection error: {e}")

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Initial push
        await manager.broadcast_alerts()
        
        while True:
            # We keep connection open and periodically push (e.g. every 30 seconds)
            # In a real enterprise system, this would be triggered by a Redis PubSub channel
            await asyncio.sleep(30)
            await manager.broadcast_alerts()
            
            # Keep receiving to handle client disconnects
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        safe_print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
