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

    async def stop_transcribe():
        await asyncio.sleep(1)
        should_stop[0] = True

    async def dummy_transcriber(items: list) -> str:
        await asyncio.sleep(0.01)
        print(items)

    items = Queue()
    items.put(1)
    should_stop = [True]
    task_stop_transcribe = asyncio.create_task(stop_transcribe())

    await st.transcribe(should_stop, items, dummy_transcriber)
    assert items.qsize() == 1

    should_stop = [False]
    await st.transcribe(should_stop, items, dummy_transcriber)
    assert items.qsize() == 0

    await task_stop_transcribe


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
