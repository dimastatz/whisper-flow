"""
capture audio from microphone
"""

import queue
import asyncio
import pyaudio
import numpy as np

from whisperflow import config


async def capture_audio(
    queue_chunks: queue.Queue, stop_event: asyncio.Event
):  # pragma: no cover
    """capture the mic stream without blocking the event loop"""
    loop = asyncio.get_running_loop()
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.SAMPLE_RATE,
        input=True,
        frames_per_buffer=config.CHUNK_SIZE,
    )

    try:
        while not stop_event.is_set():
            data = await loop.run_in_executor(None, stream.read, config.CHUNK_SIZE)
            queue_chunks.put_nowait(data)
            await asyncio.sleep(0.001)
    finally:
        stream.close()
        audio.terminate()


async def play_audio(
    queue_chunks: queue.Queue, stop_event: asyncio.Event
):  # pragma: no cover
    """play audio from queue without blocking the event loop"""
    loop = asyncio.get_running_loop()
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.SAMPLE_RATE,
        output=True,
        frames_per_buffer=config.CHUNK_SIZE,
    )

    try:
        while not stop_event.is_set():
            if not queue_chunks.empty():
                data = queue_chunks.get()
                await loop.run_in_executor(None, stream.write, data)
            await asyncio.sleep(0.001)
    finally:
        stream.close()
        audio.terminate()


def is_silent(data, silence_threshold=None):  # pragma: no cover
    """is chunk is silence"""
    threshold = (
        config.SILENCE_THRESHOLD if silence_threshold is None else silence_threshold
    )
    return np.max(np.frombuffer(data, dtype=np.int16)) < threshold
