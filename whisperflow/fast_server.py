""" fast api declaration """

import logging
from typing import List
from fastapi import FastAPI, WebSocket, Form, File, UploadFile

import whisperflow.streaming as st
import whisperflow.transcriber as ts

VERSION = "0.0.1"
app = FastAPI()


sessions = {}


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
    model = ts.get_model()

    async def transcribe_async(chunks: list):
        return await ts.transcribe_pcm_chunks_async(model, chunks)

    async def send_back_async(data: dict):
        await websocket.send_json(data)

    try:
        await websocket.accept()
        session = st.TrancribeSession(transcribe_async, send_back_async)
        sessions[session.id] = session

        while True:
            data = await websocket.receive_bytes()
            session.queue.put(data)
    except Exception as exception:  # pylint: disable=broad-except
        logging.error(exception)
        await session.stop()
        await websocket.close()
