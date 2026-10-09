""" tests for session options, silence endpointing and the protocol contract """

import asyncio
from queue import Queue

import pytest
from starlette.websockets import WebSocketDisconnect

import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.fast_server as fs
import whisperflow.transcriber as ts
from whisperflow import PROTOCOL_VERSION

SPEECH = b"\xff\x7f" * 800  # 50 ms at full scale
SILENCE = b"\x00\x00" * 800  # 50 ms of silence


# --- streaming: silence detection and normalized text ---


def test_is_silent():
    """chunks below the threshold are silent, odd trailing bytes are ignored"""
    assert st.is_silent(SILENCE)
    assert st.is_silent(b"")
    assert st.is_silent(b"\x00\x00\x7f")
    assert not st.is_silent(SPEECH)
    assert not st.is_silent(b"\x00\x80")  # -32768


def test_duration_ms():
    """chunk duration follows the sample rate"""
    assert st.duration_ms(SPEECH) == pytest.approx(50)


def test_normalize_ignores_case_and_punctuation():
    """cosmetic differences compare equal"""
    assert st.normalize(" Hello,  World! ") == st.normalize("hello world")
    prev = {"data": {"text": "Hello world."}}
    assert st.should_close_segment({"data": {"text": "hello, world"}}, prev, 1)


def test_segment_bounds_lead_in(monkeypatch):
    """silence before speech is trimmed to WF_SILENCE_MS"""
    monkeypatch.setattr(st.config, "SILENCE_MS", 100)
    segment = st.Segment()
    for _ in range(10):
        segment.add(SILENCE)
    assert len(segment.window) == 2
    assert not segment.has_speech and not segment.ended_by_silence()

    segment.add(SPEECH)
    segment.add(SILENCE)
    assert segment.has_speech and not segment.ended_by_silence()
    segment.add(SILENCE)
    assert segment.ended_by_silence()


async def run_loop(chunks: list, transcriber) -> list:
    """feed chunks through the loop, return what was sent back"""
    queue, should_stop, results = Queue(), [False], []
    for chunk in chunks:
        queue.put(chunk)

    async def collect(result: dict) -> None:
        results.append(result)

    task = asyncio.create_task(st.transcribe(should_stop, queue, transcriber, collect))
    await asyncio.sleep(0.1)
    should_stop[0] = True
    await task
    return results


@pytest.mark.asyncio
async def test_silence_closes_segment(monkeypatch):
    """a pause of WF_SILENCE_MS after speech sends a final on the next cycle"""
    monkeypatch.setattr(st.config, "SILENCE_MS", 100)
    calls = []

    async def changing(items: list) -> dict:
        calls.append(len(items))
        return {"text": f"words {len(calls)}"}  # never stable

    results = await run_loop([SPEECH, SILENCE, SILENCE], changing)
    assert results[0]["is_partial"] is False
    assert results[0]["data"]["text"] == "words 1"
    assert calls[0] == 3


@pytest.mark.asyncio
async def test_silence_only_is_not_transcribed():
    """windows with no speech are never sent to the model"""
    calls = []

    async def record(items: list) -> dict:
        calls.append(items)
        return {"text": "hallucination"}

    request = st.FlushRequest()
    results = await run_loop([SILENCE, SILENCE, request], record)
    assert request.done.done()
    assert not calls and not results


# --- transcriber: prompt + model listing ---


class FakeModel:  # pylint: disable=too-few-public-methods
    """records the kwargs passed to transcribe"""

    def __init__(self):
        """ctor"""
        self.kwargs = {}

    def transcribe(self, _audio, **kwargs):
        """record and return an empty result"""
        self.kwargs = kwargs
        return {"text": ""}


@pytest.mark.asyncio
async def test_prompt_passed_as_initial_prompt():
    """the prompt reaches whisper as initial_prompt; default is none"""
    model = FakeModel()
    ts.transcribe_pcm_chunks(model, [SILENCE])
    assert model.kwargs["initial_prompt"] is None
    await ts.transcribe_pcm_chunks_async(model, [SILENCE], "de", prompt="useMemo")
    assert model.kwargs["initial_prompt"] == "useMemo"
    assert model.kwargs["language"] == "de"


def test_check_prompt(monkeypatch):
    """prompts are optional, must be strings and are length-limited"""
    monkeypatch.setattr(ts.config, "MAX_PROMPT_CHARS", 5)
    assert ts.check_prompt(None) is None
    assert ts.check_prompt("") is None
    assert ts.check_prompt("abc") == "abc"
    with pytest.raises(ValueError):
        ts.check_prompt("abcdef")
    with pytest.raises(ValueError):
        ts.check_prompt(42)


def test_list_models():
    """the bundled model is listed"""
    assert "tiny.en.pt" in ts.list_models()


# --- fast_server: /ready, http prompt, start frame ---


def test_ready_reports_protocol_and_models():
    """/ready exposes the protocol version and the available models"""
    body = ut.TestClient(fs.app).get("/ready").json()
    assert body["protocol_version"] == PROTOCOL_VERSION
    assert "tiny.en.pt" in body["models"]


def test_http_prompt(monkeypatch):
    """the http endpoint accepts a prompt and rejects one that is too long"""
    monkeypatch.setattr(ts.config, "MAX_PROMPT_CHARS", 10)
    client = ut.TestClient(fs.app)
    files = [("files", ("a.pcm", SILENCE, "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt", "prompt": "getUserById"}
    assert (
        client.post("/transcribe_pcm_chunk", files=files, data=data).status_code == 400
    )
    data["prompt"] = "useMemo"
    assert (
        client.post("/transcribe_pcm_chunk", files=files, data=data).status_code == 200
    )


@pytest.mark.parametrize(
    "start",
    [
        '{"type": "start", "model": "missing.pt"}',
        '{"type": "start", "model": "../evil.pt"}',
        '{"type": "start", "language": "klingon"}',
        '{"type": "start", "prompt": 42}',
    ],
)
def test_ws_start_invalid_options(start):
    """invalid start options close the socket with code 4000 and a reason"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(start)
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
    assert error.value.code == fs.CLOSE_INVALID_OPTIONS
    assert error.value.reason


def test_ws_start_options_applied(monkeypatch):
    """model, language and prompt from start are used for the session"""
    seen = {}

    async def fake(model, _chunks, lang="en", prompt=None, word_timestamps=False):
        seen.update(model=model, lang=lang, prompt=prompt, words=word_timestamps)
        return {"text": "hello"}

    monkeypatch.setattr(fs.ts, "transcribe_pcm_chunks_async", fake)
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(
            '{"type": "start", "model": "tiny.en.pt", "language": "en",'
            ' "prompt": "useMemo"}'
        )
        websocket.send_bytes(SPEECH)
        websocket.send_text('{"type": "stop"}')
        while websocket.receive_json()["is_partial"]:
            pass

    assert seen == {
        "model": ts.get_model("tiny.en.pt"),
        "lang": "en",
        "prompt": "useMemo",
        "words": False,
    }
