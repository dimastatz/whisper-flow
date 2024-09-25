""" 
a test app that streams 
audio  from the mic to whisper flow
requires pip install PyAudio
"""

import json
import asyncio
import pyaudio
import websockets


async def start_transcription(url="ws://0.0.0.0:8181/ws"):
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
        try:
            result = json.loads(websocket.recv())
            print(result["is_partial"], round(result["time"], 2), result["data"]["text"]) 
        except websockets.WebSocketTimeoutException:
            print("No transcription available")
            await asyncio.sleep(0.1)


asyncio.run(start_transcription())
