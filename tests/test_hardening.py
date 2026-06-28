""" tests for P0/P1 hardening: validation, limits, auth, lifecycle """

import asyncio

import pytest

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


def test_trim_window():
    """window is trimmed to the most recent chunks"""
    assert st.trim_window([1, 2, 3], 2) == [2, 3]
    assert st.trim_window([1], 2) == [1]


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
