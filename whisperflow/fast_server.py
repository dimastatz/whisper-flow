""" fast api declaration """

import logging
from typing import List
from fastapi import FastAPI, WebSocket, Form, File, UploadFile

import whisperflow.transcriber as ts


VERSION = "0.0.1"
app = FastAPI()


@app.get("/health", response_model=str)
def health():
    """health function on API"""
    return f"Whisper Flow V{VERSION}"


@app.post("/transcribe_pcm_chunk", response_model=dict)
def transcribe_pcm_chunk(
    model_name: str = Form(...), files: List[UploadFile] = File(...)
):
    """transcribe chunk"""
    model = ts.get_model(model_name)
    content = files[0].file.read()
    return ts.transcribe_pcm_chunks(model, [content])


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
