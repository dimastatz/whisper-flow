""" tests for P0/P1 hardening: validation, limits, auth, lifecycle """

import json
import time
import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect

import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.fast_server as fs
import whisperflow.transcriber as ts


# --- transcriber: model-name validation ---


def test_resolve_model_path_rejects_traversal():
    """path traversal in a model name is rejected"""
    with pytest.raises(ValueError):
        ts.resolve_model_path("../secrets.pt")


def test_get_model_unknown():
    """an unknown (but in-dir) model name is rejected"""
    with pytest.raises(ValueError):
        ts.get_model("does-not-exist.pt")


# --- streaming: bounding + safe transcription ---


@pytest.mark.asyncio
async def test_safe_transcribe_error():
    """a failing transcriber yields None instead of crashing"""

    async def boom(_window):
        raise RuntimeError("fail")

    assert await st.safe_transcribe(boom, [b"x"]) is None


@pytest.mark.asyncio
async def test_safe_transcribe_timeout(monkeypatch):
    """a slow transcriber times out and yields None"""
    monkeypatch.setattr(st.config, "TRANSCRIBE_TIMEOUT", 0.01)

    async def slow(_window):
        await asyncio.sleep(1)
        return {"text": "x"}

    assert await st.safe_transcribe(slow, [b"x"]) is None


@pytest.mark.asyncio
async def test_queue_bounded_while_model_busy(monkeypatch):
    """audio sent while the model is busy must not queue without limit (#64)"""
    monkeypatch.setattr(st.config, "MAX_WINDOW_CHUNKS", 2)
    busy = asyncio.Event()

    async def slow(_window, **_kwargs):
        busy.set()
        await asyncio.sleep(1)
        return {"text": "x"}

    async def sink(_data):
        pass

    session = st.TranscribeSession(slow, sink)
    session.add_chunk(b"\xff\x7f" * 1024)
    await busy.wait()
    for _ in range(100):
        session.add_chunk(b"\xff\x7f" * 1024)

    queued = session.queue.qsize()
    session.task.cancel()
    assert queued <= st.config.MAX_WINDOW_CHUNKS


@pytest.mark.asyncio
async def test_queue_bounded_by_bytes(monkeypatch):
    """a chunk that would exceed WF_MAX_QUEUED_BYTES is refused"""
    monkeypatch.setattr(st.config, "MAX_QUEUED_BYTES", 4)

    async def unused(*_args, **_kwargs):
        pass

    session = st.TranscribeSession(unused, unused)
    assert session.add_chunk(b"\x00" * 4)
    assert not session.add_chunk(b"\x00\x00")
    assert session.queue.queued_bytes == 4
    session.task.cancel()


def test_ws_overload_closes(monkeypatch):
    """the socket closes with CLOSE_OVERLOADED when the backlog is full"""
    monkeypatch.setattr(fs.config, "MAX_QUEUED_BYTES", 0)
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_bytes(b"\x00\x00")
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
    assert error.value.code == fs.CLOSE_OVERLOADED
    assert not fs.sessions


# --- fast_server: readiness, limits, auth ---


def test_ready():
    """readiness endpoint reports session/model state"""
    client = ut.TestClient(fs.app)
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "active_sessions" in body


def test_upload_too_large(monkeypatch):
    """oversized uploads are rejected with 413"""
    monkeypatch.setattr(fs.config, "MAX_UPLOAD_BYTES", 1)
    client = ut.TestClient(fs.app)
    files = [("files", ("a.pcm", b"abcdef", "application/octet-stream"))]
    res = client.post(
        "/transcribe_pcm_chunk", files=files, data={"model_name": "tiny.en.pt"}
    )
    assert res.status_code == 413


def test_invalid_model_name():
    """an invalid model name is rejected with 400"""
    client = ut.TestClient(fs.app)
    files = [("files", ("a.pcm", b"abcd", "application/octet-stream"))]
    res = client.post(
        "/transcribe_pcm_chunk", files=files, data={"model_name": "../evil.pt"}
    )
    assert res.status_code == 400


def test_api_key_required(monkeypatch):
    """a configured API key is enforced on the http endpoint"""
    monkeypatch.setattr(fs.config, "API_KEY", "secret")
    client = ut.TestClient(fs.app)
    files = [("files", ("a.pcm", b"abcd", "application/octet-stream"))]
    res = client.post(
        "/transcribe_pcm_chunk", files=files, data={"model_name": "tiny.en.pt"}
    )
    assert res.status_code == 401


def test_api_key_accepted(monkeypatch):
    """a matching API key is accepted on the http endpoint"""
    monkeypatch.setattr(fs.config, "API_KEY", "secret")
    client = ut.TestClient(fs.app)
    files = [("files", ("a.pcm", b"\x00\x00\x00\x00", "application/octet-stream"))]
    res = client.post(
        "/transcribe_pcm_chunk",
        files=files,
        data={"model_name": "tiny.en.pt"},
        headers={"x-api-key": "secret"},
    )
    assert res.status_code == 200


def test_ws_requires_api_key(monkeypatch):
    """websocket connections are rejected without the configured key"""
    monkeypatch.setattr(fs.config, "API_KEY", "secret")
    client = ut.TestClient(fs.app)
    with pytest.raises(Exception):  # pylint: disable=broad-exception-caught
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_bytes()


def test_ws_session_cap(monkeypatch):
    """websocket connections are rejected when the session cap is reached"""
    monkeypatch.setattr(fs.config, "MAX_SESSIONS", 0)
    client = ut.TestClient(fs.app)
    with pytest.raises(Exception):  # pylint: disable=broad-exception-caught
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_bytes()


def test_ws_cleans_up_sessions():
    """a disconnected session is removed from the registry"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_bytes(b"\x00\x00")
    assert len(fs.sessions) == 0


@pytest.mark.asyncio
async def test_stop_all_sessions():
    """shutdown drains and clears all active sessions"""

    class FakeSession:  # pylint: disable=too-few-public-methods
        """minimal stand-in for a TranscribeSession"""

        def __init__(self):
            """ctor"""
            self.id = "fake"  # pylint: disable=invalid-name
            self.stopped = False

        async def stop(self):
            """record that stop was called"""
            self.stopped = True

    fake = FakeSession()
    fs.sessions[fake.id] = fake
    await fs.stop_all_sessions()
    assert fake.stopped
    assert not fs.sessions


def test_ws_disconnect_mid_transcription(monkeypatch):
    """a client dropping mid-transcription doesn't leak its session (#49)"""

    async def slow_transcribe(*_args, **_kwargs):
        """stand-in transcriber that is still running when the client drops"""
        await asyncio.sleep(0.3)
        return {"text": "hello"}

    async def closed_send_json(*_args, **_kwargs):
        """what uvicorn does on a send after the client is gone"""
        raise RuntimeError("Unexpected ASGI message 'websocket.send'")

    send_json = fs.WebSocket.send_json
    monkeypatch.setattr(fs.config, "MAX_SESSIONS", 1)
    monkeypatch.setattr(fs.ts, "transcribe_pcm_chunks_async", slow_transcribe)
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_bytes(b"\xff\x7f" * 1600)
        time.sleep(0.1)
        monkeypatch.setattr(fs.WebSocket, "send_json", closed_send_json)
    assert len(fs.sessions) == 0
    monkeypatch.setattr(fs.WebSocket, "send_json", send_json)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"type": "stop"}))
    assert len(fs.sessions) == 0
