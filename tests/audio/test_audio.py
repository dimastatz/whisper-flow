""" test chat room """

import queue
import asyncio
import pytest
import numpy as np
import whisperflow.audio.microphone as mic


@pytest.mark.asyncio
async def test_capture_mic():
    """test capturing microphone"""
    stop_event = asyncio.Event()
    audio_chunks = queue.Queue()

    async def stop_capturing():
        await asyncio.sleep(0.1)
        stop_event.set()

    await asyncio.gather(mic.capture_audio(audio_chunks, stop_event), stop_capturing())
    assert stop_event.is_set()
    assert not audio_chunks.empty()


def test_is_silent():
    """test silence detection"""
    silence_threshold = 500
    # Create a silent audio buffer (all zeros)
    silent_data = np.zeros(1024, dtype=np.int16).tobytes()
    assert mic.is_silent(silent_data), "Silent data should be detected as silent"

    # Create a loud audio buffer (above threshold)
    loud_data = (np.ones(1024, dtype=np.int16) * (silence_threshold + 1000)).tobytes()
    assert not mic.is_silent(loud_data), "Loud data should not be detected as silent"

    # Create a borderline case (right at the threshold)
    threshold_data = (np.ones(1024, dtype=np.int16) * silence_threshold).tobytes()
    assert not mic.is_silent(
        threshold_data
    ), "Threshold-level data should not be detected as silent"


@pytest.mark.asyncio
async def test_play_audio():
    """
    Test the play_audio function by adding dummy audio data to a queue,
    running the function, and ensuring the queue is empty after processing.
    """
    queue_chunks = queue.Queue()
    stop_event = asyncio.Event()

    # Add some dummy audio data to the queue
    dummy_data = b"\x00\x01" * 1024 * 10  # 2MB per sample, 1024 samples
    queue_chunks.put(dummy_data)

    # Run play_audio in a separate task
    play_task = asyncio.create_task(mic.play_audio(queue_chunks, stop_event))

    # Allow some time for play_audio to process the queue
    await asyncio.sleep(0.1)

    # Stop the play_audio function
    stop_event.set()
    await play_task

    # Check that the queue is empty after processing
    assert queue_chunks.empty()
