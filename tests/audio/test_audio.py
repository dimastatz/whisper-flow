""" test chat room """

import queue
import pytest
import asyncio


from whisperflow.audio.microphone import capture_audio


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
