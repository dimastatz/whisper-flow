"""
capture audio from microphone
"""

import queue
import asyncio
import pyaudio
import numpy as np


async def capture_audio(queue_chunks: queue.Queue, stop_event: asyncio.Event):
    """capture the mic stream"""
    chunk, rate, record_sec = 1024, 16000, 1
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=chunk,
    )

    while not stop_event.is_set():
        for _ in range(0, int(rate / chunk * record_sec)):
            data = stream.read(chunk)
            queue_chunks.put(data)
            await asyncio.sleep(0.01)

    stream.close()
    audio.terminate()


async def play_audio(queue_chunks: queue.Queue, stop_event: asyncio.Event):
    """play audio from queue"""
    chunk, rate = 1024, 16000
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        output=True,
        frames_per_buffer=chunk,
    )

    while not stop_event.is_set():
        if not queue_chunks.empty():
            data = queue_chunks.get()
            stream.write(data)
        await asyncio.sleep(0.001)

    stream.close()
    audio.terminate()


def is_silent(data, silence_threshold=500):
    """is chunk is silence"""
    return np.max(np.frombuffer(data, dtype=np.int16)) < silence_threshold
