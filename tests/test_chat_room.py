""" test chat room """

import queue
import asyncio
from whisperflow.chat_room import ChatRoom


async def stop_chat_room(room: ChatRoom):
    """stop chat room loop"""
    await asyncio.sleep(0.1)
    assert room.chat_started
    room.stop_chat()
    await asyncio.sleep(0.1)  # Give some time for tasks to stop
    assert room.chat_started is False


async def listener_mock(queue: queue.Queue, stop_event: asyncio.Event):
    """collect items from queue"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        queue.put("hello")


async def processor_mock(queue_in, queue_out, stop_event):
    """collect items from queue"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        if not queue_in.empty():
            item = queue_in.get()
            queue_out.put(item)


async def speaker_mock(queue: queue.Queue, stop_event: asyncio.Event):
    """mock playing sound"""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        if not queue.empty():
            item = queue.get()
            assert item is not None


async def test_chat_room():
    room = ChatRoom(listener_mock, speaker_mock, processor_mock)
    await room.start_chat()
    await stop_chat_room(room)
    assert room.stop_chat.is_set()
