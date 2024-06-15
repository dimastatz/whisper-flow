""" test scenario module """

import asyncio
from queue import Queue

import pytest
from starlette.testclient import TestClient

import whisperflow.streaming as st
import whisperflow.fast_server as fs


@pytest.mark.asyncio
async def test_simple():
    """test asyncio"""

    queue, should_stop = Queue(), [False]
    queue.put(1)

    async def dummy_transcriber(items: list) -> str:
        await asyncio.sleep(0.1)
        if queue.qsize() == 0:
            should_stop[0] = True
        return str(len(items))

    async def dummy_segment_closed(text: str) -> None:
        await asyncio.sleep(0.01)
        print(text)

    await st.transcribe(should_stop, queue, dummy_transcriber, dummy_segment_closed)
    assert queue.qsize() == 0


def test_streaming():
    """test hugging face image generation"""
    queue = Queue()
    queue.put(1)
    queue.put(2)
    res = st.get_all(queue)
    assert res == [1, 2]

    res = st.get_all(None)
    assert not res


def test_fast_api():
    """test health api"""
    with TestClient(fs.app) as client:
        response = client.get("/health")
        assert response.status_code == 200 and bool(response.text)


@pytest.mark.asyncio
async def test_ws():
    """test health api"""
    client = TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, world 1")
        data = websocket.receive_bytes()
        assert data == b"Hello, world 1"

        websocket.send_text("Hello, world 2")
        data = websocket.receive_bytes()
        assert data == b"Hello, world 2"

        websocket.close()
