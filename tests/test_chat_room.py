""" test chat room """

import pytest
from whisperflow.chat_room import ChatRoom


@pytest.mark.asyncio
async def test_chat_room():
    """test chat room simple flow"""
    room = ChatRoom()
    assert room.chat_started is False
