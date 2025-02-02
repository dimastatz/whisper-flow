"""
capture audio from microphone
"""

import queue
import asyncio
import pyaudio


async def capture_audio(queue_chunks: queue.Queue, stop_event: asyncio.Event):
    """capture the mic stream"""
    chunk, rate, record_sec = 1024, 16000, 30
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=chunk,
    )
    print("* recording")

    for _ in range(0, int(rate / chunk * record_sec)):
        data = stream.read(chunk)
        await queue_chunks.send(data)
        await asyncio.sleep(0.01)

    stream.close()
    p.terminate()