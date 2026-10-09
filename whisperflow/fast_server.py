""" fast api declaration """

import json
import asyncio
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Form,
    File,
    UploadFile,
    Header,
    Depends,
    HTTPException,
)

from whisper.tokenizer import LANGUAGES

from whisperflow import __version__, PROTOCOL_VERSION, config
import whisperflow.streaming as st
import whisperflow.transcriber as ts


LOG = logging.getLogger(__name__)
sessions = {}

# close code for a start frame with invalid options (see docs/protocol.md)
CLOSE_INVALID_OPTIONS = 4000


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
        "protocol_version": PROTOCOL_VERSION,
        "models": ts.list_models(),
        "model_loaded": bool(ts.models),
        "active_sessions": len(sessions),
    }


@app.post("/transcribe_pcm_chunk", response_model=dict)
def transcribe_pcm_chunk(
    model_name: str = Form(...),
    files: List[UploadFile] = File(...),
    prompt: Optional[str] = Form(default=None),
    _: None = Depends(require_api_key),
):
    """transcribe a single uploaded pcm chunk"""
    content = files[0].file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    try:
        prompt = ts.check_prompt(prompt)
        model = ts.get_model(model_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ts.transcribe_pcm_chunks(model, [content], prompt=prompt)


async def parse_start(message: dict) -> dict:
    """validate start-frame options; raise ValueError on a bad one"""
    options = {"prompt": ts.check_prompt(message.get("prompt"))}
    language = message.get("language")
    if language is not None:
        if language not in LANGUAGES:
            raise ValueError(f"unknown language: {language}")
        options["lang"] = language
    name = message.get("model")
    if name is not None:
        ts.resolve_model_path(str(name))
        options["model"] = await asyncio.get_running_loop().run_in_executor(
            None, ts.get_model, str(name)
        )
    return options


async def handle_control(
    websocket: WebSocket, session, options: dict, text: str
) -> bool:
    """apply a JSON control frame; return True when the socket was closed"""
    try:
        message = json.loads(text)
        kind = message.get("type")
    except (ValueError, AttributeError):
        kind = None

    if kind == "start":
        try:
            options.update(await parse_start(message))
        except ValueError as error:
            await websocket.close(code=CLOSE_INVALID_OPTIONS, reason=str(error)[:120])
            return True
    elif kind in ("flush", "stop"):
        await session.flush()
    else:
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

    options = {"model": ts.get_model(), "lang": "en", "prompt": None}
    session = None

    async def transcribe_async(chunks: list, context: str = "", words: bool = False):
        # the vocabulary prompt first, then the segment's committed text
        prompt = " ".join(part for part in (options["prompt"], context) if part)
        return await ts.transcribe_pcm_chunks_async(
            options["model"],
            chunks,
            options["lang"],
            prompt=prompt or None,
            word_timestamps=words,
        )

    async def send_back_async(data: dict):
        # an in-flight result can land after the client is gone; drop it
        try:
            await websocket.send_json(data)
        except (RuntimeError, OSError, WebSocketDisconnect):
            LOG.debug("dropped result for a disconnected client")

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
            elif await handle_control(
                websocket, session, options, message.get("text", "")
            ):
                break
    except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover
        LOG.exception("websocket error")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
    finally:
        if session:
            try:
                await session.stop()
            finally:
                sessions.pop(session.id, None)
