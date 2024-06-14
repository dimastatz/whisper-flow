""" fast api declaration """

import logging
from fastapi import FastAPI, WebSocket


app = FastAPI()
VERSION = "0.1.0"


@app.get("/health", response_model=str)
def health():
    """health function on API"""
    return f"Whisper Flow V{VERSION}"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """webscoket implementation"""
    try:
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_bytes(data.encode("ascii"))
    except Exception as exception:  # pylint: disable=broad-except
        logging.error(exception)
        await websocket.close()
