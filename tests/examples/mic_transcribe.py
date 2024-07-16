""" 
a test app that streams 
audio  from the mic to whisper flow
requires pip install PyAudio
"""

import asyncio
import pyaudio
import websockets


async def start_transcription(url="http://0.0.0.0:8181"):
    """stream mic audio to server"""
    async with websockets.connect(url) as websocket:
        await asyncio.gather(capture_audio(websocket), receive_transcription(websocket))


async def capture_audio(websocket: websockets.WebSocketClientProtocol):
    """capture the mic stream"""
    chunk, rate, record_sec = 1024, 16000, 5
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
        await websocket.send(data)

    stream.close()
    p.terminate()
    print("* done recording")


async def receive_transcription(websocket):
    """print transcription"""
    while True:
        text_data = await websocket.recv()
        print(text_data)


asyncio.run(start_transcription())
