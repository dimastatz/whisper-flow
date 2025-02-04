""" test chat room """

import queue
import asyncio
import pytest

from whisperflow.chat_room import ChatRoom
from whisperflow.microphone import capture_audio


async def listener_mock(queue_in: queue.Queue, stop_event: asyncio.Event):
    """collect items from queue"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        queue_in.put("hello")


async def processor_mock(queue_in, queue_out, stop_event):
    """collect items from queue"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        if not queue_in.empty():
            item = queue_in.get()
            queue_out.put(item)


async def speaker_mock(queue_in: queue.Queue, stop_event: asyncio.Event):
    """mock playing sound"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        if not queue_in.empty():
            item = queue_in.get()
            assert item is not None


@pytest.mark.asyncio
async def test_chat_room():
    """mock playing sound"""
    room = ChatRoom(listener_mock, speaker_mock, processor_mock)

    async def stop_chat():
        await asyncio.sleep(1)
        room.stop_chat()

    await asyncio.gather(room.start_chat(), stop_chat())
    assert room.stop_chat_event.is_set()


@pytest.mark.asyncio
async def test_capture_mic():
    """test capturing microphone"""
    stop_event = asyncio.Event()
    audio_chunks = queue.Queue()

    async def stop_capturing():
        await asyncio.sleep(0.1)
        stop_event.set()

    await asyncio.gather(capture_audio(audio_chunks, stop_event), stop_capturing())
    assert stop_event.is_set()
    assert not audio_chunks.empty()
