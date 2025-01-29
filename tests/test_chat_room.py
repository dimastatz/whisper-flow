""" test chat room """

import queue
import asyncio
import pytest
from whisperflow.chat_room import ChatRoom


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
    await room.start_chat()
    await asyncio.sleep(0.1)
    room.stop_chat()
    assert room.stop_chat_event.is_set()
