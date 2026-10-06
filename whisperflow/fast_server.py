""" fast api declaration """

import json
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    WebSocket,
    Form,
    File,
    UploadFile,
    Header,
    Depends,
    HTTPException,
)

from whisperflow import __version__, config
import whisperflow.streaming as st
import whisperflow.transcriber as ts


LOG = logging.getLogger(__name__)
sessions = {}


async def stop_all_sessions():
    """stop and drop every active session (used on shutdown)"""
    for session in list(sessions.values()):
        await session.stop()
    sessions.clear()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """preload the default model on startup and drain sessions on shutdown"""
    ts.get_model()
    yield
    await stop_all_sessions()


app = FastAPI(lifespan=lifespan)


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """reject the request when an API key is configured but not matched"""
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing api key")


@app.get("/health", response_model=str)
def health():
    """liveness probe"""
    return f"Whisper Flow V{__version__}"


@app.get("/ready", response_model=dict)
def ready():
    """readiness probe reporting model and session state"""
    return {
        "status": "ok",
        "version": __version__,
        "model_loaded": bool(ts.models),
        "active_sessions": len(sessions),
    }


@app.post("/transcribe_pcm_chunk", response_model=dict)
def transcribe_pcm_chunk(
    model_name: str = Form(...),
    files: List[UploadFile] = File(...),
    _: None = Depends(require_api_key),
):
    """transcribe a single uploaded pcm chunk"""
    content = files[0].file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    try:
        model = ts.get_model(model_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ts.transcribe_pcm_chunks(model, [content])


async def handle_control(websocket: WebSocket, session, text: str) -> bool:
    """apply a JSON control frame; return True when the socket should close"""
    try:
        message = json.loads(text)
        kind = message.get("type")
    except (ValueError, AttributeError):
        kind = None

    if kind in ("flush", "stop"):
        await session.flush()
    elif kind != "start":  # start options are accepted but not used yet
        await websocket.send_json({"type": "error", "message": "invalid control"})

    if kind == "stop":
        await websocket.close()
        return True
    return False


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """websocket streaming transcription endpoint"""
    if config.API_KEY and websocket.headers.get("x-api-key") != config.API_KEY:
        await websocket.close(code=1008)
        return
    if len(sessions) >= config.MAX_SESSIONS:
        await websocket.close(code=1013)
        return

    model = ts.get_model()
    session = None

    async def transcribe_async(chunks: list):
        return await ts.transcribe_pcm_chunks_async(model, chunks)

    async def send_back_async(data: dict):
        await websocket.send_json(data)

    try:
        await websocket.accept()
        session = st.TranscribeSession(transcribe_async, send_back_async)
        sessions[session.id] = session

        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message.get("bytes") is not None:
                session.add_chunk(message["bytes"])
            elif await handle_control(websocket, session, message.get("text", "")):
                break
    except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover
        LOG.exception("websocket error")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
    finally:
        if session:
            await session.stop()
            sessions.pop(session.id, None)
