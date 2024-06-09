""" fast api declaration """

from fastapi import FastAPI
from fastapi.websockets import WebSocket


app = FastAPI()


@app.get("/health", response_model=bool)
def health():
    """health function on API"""
    return True


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """webscoket implementation"""
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})
    await websocket.close()
