""" test scenario module """

import asyncio
from queue import Queue

import pytest
import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.fast_server as fs
import whisperflow.transcriber as ts


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


@pytest.mark.asyncio
async def test_transcribe_streaming(chunk_size=4096):
    """test streaming"""

    model = ts.get_model()
    queue, should_stop = Queue(), [False]
    res = ut.load_resource("3081-166546-0000")
    chunks = [
        res["audio"][i : i + chunk_size]
        for i in range(0, len(res["audio"]), chunk_size)
    ]

    async def dummy_transcriber(items: list) -> str:
        await asyncio.sleep(0.01)
        result = ts.transcribe_pcm_chunks(model, items)
        return result["text"].lower()

    result = []

    async def dummy_segment_closed(text: str) -> None:
        await asyncio.sleep(0.01)
        result.append(text)

    task = asyncio.create_task(
        st.transcribe(should_stop, queue, dummy_transcriber, dummy_segment_closed)
    )

    for chunk in chunks:
        queue.put(chunk)
        await asyncio.sleep(0.01)

    await asyncio.sleep(1)
    should_stop[0] = True
    await task

    assert len(result) > 0


def test_streaming():
    """test hugging face image generation"""
    queue = Queue()
    queue.put(1)
    queue.put(2)
    res = st.get_all(queue)
    assert res == [1, 2]

    res = st.get_all(None)
    assert not res


@pytest.mark.asyncio
async def test_ws(chunk_size=4096):
    """test health api"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        res = ut.load_resource("3081-166546-0000")
        chunks = [
            res["audio"][i : i + chunk_size]
            for i in range(0, len(res["audio"]), chunk_size)
        ]

        websocket.send_bytes(chunks[0])
        res = websocket.recieve_json()
        assert res

        websocket.close()
