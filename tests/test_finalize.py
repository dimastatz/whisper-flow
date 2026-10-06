""" tests for finalize-on-stop/flush and the window cap """

import asyncio
from queue import Queue

import pytest

import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.fast_server as fs


async def join_transcriber(items: list) -> dict:
    """fake transcriber: the window's chunks joined into one string"""
    return {"text": b"".join(items).decode()[::2]}


def run_loop(queue: Queue, results: list, transcriber=join_transcriber):
    """start the transcription loop collecting results"""
    should_stop = [False]

    async def collect(result: dict) -> None:
        results.append(result)

    task = asyncio.create_task(st.transcribe(should_stop, queue, transcriber, collect))
    return should_stop, task


# --- streaming: window cap ---


@pytest.mark.asyncio
async def test_window_cap_closes_segment(monkeypatch):
    """reaching the cap sends the segment as final instead of dropping its start"""
    monkeypatch.setattr(st.config, "MAX_WINDOW_CHUNKS", 3)
    queue, results = Queue(), []
    for chunk in [b"aa", b"bb", b"cc", b"dd", b"ee", b"ff", b"gg"]:
        queue.put(chunk)

    should_stop, task = run_loop(queue, results)
    await asyncio.sleep(0.1)
    should_stop[0] = True
    await task

    finals = [r["data"]["text"] for r in results if not r["is_partial"]]
    assert finals[:2] == ["abc", "def"]
    assert "".join(finals).startswith("abcdefg")


# --- streaming: flush ---


@pytest.mark.asyncio
async def test_flush_sends_final_with_queued_audio():
    """flush finalizes everything queued before it, in order"""

    async def slow(items: list) -> dict:
        await asyncio.sleep(0.05)
        return await join_transcriber(items)

    queue, results = Queue(), []
    should_stop, task = run_loop(queue, results, slow)

    request = st.FlushRequest()
    for item in [b"aa", b"bb", request, b"cc"]:
        queue.put(item)
    await request.done

    assert results[-1]["is_partial"] is False
    assert results[-1]["data"]["text"] == "ab"
    should_stop[0] = True
    await task


@pytest.mark.asyncio
async def test_flush_empty_window_sends_nothing():
    """flush with no pending audio resolves without sending a result"""
    queue, results = Queue(), []
    should_stop, task = run_loop(queue, results)

    request = st.FlushRequest()
    queue.put(request)
    await request.done
    should_stop[0] = True
    await task

    assert not results


@pytest.mark.asyncio
async def test_session_flush():
    """the session flush waits until the final result is sent"""
    results = []

    async def collect(result: dict) -> None:
        results.append(result)

    session = st.TranscribeSession(join_transcriber, collect)
    session.add_chunk(b"xx")
    session.add_chunk(b"yy")
    await session.flush()
    await session.stop()

    assert results[-1]["is_partial"] is False
    assert results[-1]["data"]["text"] == "xy"


@pytest.mark.asyncio
async def test_session_flush_after_stop():
    """flush does not hang when the loop has already exited"""

    async def ignore(_result: dict) -> None:
        return None

    session = st.TranscribeSession(join_transcriber, ignore)
    await session.stop()
    await asyncio.wait_for(session.flush(), timeout=1)


# --- fast_server: control frames ---


def send_audio(websocket, chunk_size=4096):
    """stream the test recording as binary frames"""
    audio = ut.load_resource("3081-166546-0000")["audio"]
    for i in range(0, len(audio), chunk_size):
        websocket.send_bytes(audio[i : i + chunk_size])


def receive_final(websocket) -> dict:
    """read results until the first final one"""
    while True:
        result = websocket.receive_json()
        if not result["is_partial"]:
            return result


@pytest.mark.timeout(120)
def test_ws_stop_sends_final():
    """stop returns a final result with the last words, then closes"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text('{"type": "start", "language": "en"}')
        send_audio(websocket)
        websocket.send_text('{"type": "stop"}')
        final = receive_final(websocket)
        assert final["data"]["text"].strip()
        with pytest.raises(Exception):  # pylint: disable=broad-exception-caught
            websocket.receive_json()
    assert not fs.sessions


@pytest.mark.timeout(120)
def test_ws_flush_keeps_socket_open():
    """flush returns a final result and the session keeps accepting audio"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        send_audio(websocket)
        websocket.send_text('{"type": "flush"}')
        assert receive_final(websocket)["data"]["text"].strip()
        websocket.send_bytes(b"\x00\x00")


@pytest.mark.parametrize("text", ["not json", "[1]", '{"type": "nope"}'])
def test_ws_invalid_control(text):
    """malformed or unknown control frames get an error reply"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(text)
        assert websocket.receive_json() == {
            "type": "error",
            "message": "invalid control",
        }
