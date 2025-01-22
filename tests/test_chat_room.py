""" test chat room """

import asyncio
import pytest
from whisperflow.chat_room import ChatRoom


@pytest.mark.asyncio
async def test_chat_room():
    """test chat room simple flow"""
    room = ChatRoom()
    assert room.chat_started is False

    await asyncio.gather(room.start_chat(), stop_chat_room(room))

    assert room.chat_started is False


async def stop_chat_room(room: ChatRoom):
    """stop chat room loop"""
    await asyncio.sleep(0.1)
    assert room.chat_started
    room.stop_chat()
    assert room.chat_started is False
