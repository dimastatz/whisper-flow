""" fast api declaration """

from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.get("/health", response_model=bool)
def health():
    """health function on API"""
    return True


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """webscoket implementation"""
    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_bytes(data.encode("ascii"))
    await websocket.close()
