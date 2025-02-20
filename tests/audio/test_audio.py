""" test chat room """

import queue
import asyncio
import pytest
import numpy as np
from whisperflow.audio.microphone import capture_audio, is_silent


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


def test_is_silent():
    """test silence detection"""
    silence_threshold = 500
    # Create a silent audio buffer (all zeros)
    silent_data = np.zeros(1024, dtype=np.int16).tobytes()
    assert is_silent(silent_data), "Silent data should be detected as silent"

    # Create a loud audio buffer (above threshold)
    loud_data = (np.ones(1024, dtype=np.int16) * (silence_threshold + 1000)).tobytes()
    assert not is_silent(loud_data), "Loud data should not be detected as silent"

    # Create a borderline case (right at the threshold)
    threshold_data = (np.ones(1024, dtype=np.int16) * silence_threshold).tobytes()
    assert not is_silent(
        threshold_data
    ), "Threshold-level data should not be detected as silent"
