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
        result = []
        await asyncio.gather(capture_audio(websocket, result), receive_transcription(websocket, result))
        print(f"* done recording, collecting data")
        print("Colllected text is \n", " ".join(result))
        

async def capture_audio(websocket: websockets.WebSocketClientProtocol, result: list):
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
        await websocket.send(data)
        await asyncio.sleep(0.01)
        
    stream.close()
    p.terminate()
   

async def receive_transcription(websocket, result: list):
    """print transcription"""
    while True:
        try:
            await asyncio.sleep(0.01)
            tmp = json.loads(await websocket.recv())
            if not tmp["is_partial"]:
                result.append(tmp["data"]["text"])
            print(tmp["is_partial"], round(tmp["time"], 2), tmp["data"]["text"]) 
        except Exception:
            print("No transcription available")
           

asyncio.run(start_transcription())
