"""benchamrk"""
from pathlib import Path

import json
import requests
import websocket as ws
import tests.utils as ut


def test_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url, timeout=1)
    assert result.status_code == 200


def get_res(websocket):
    """try read with timout"""
    try:
        return websocket.recv()
    except ws.WebSocketTimeoutException:
        return ""


def test_send_chunks(url="ws://localhost:8181/ws", chunk_size=4096):
    """send chunks"""
    folder = Path(__file__).resolve().parents[1]
    assert folder
    assert chunk_size

    websocket = ws.create_connection(url)
    websocket.settimeout(0.1)

    res = ut.load_resource("3081-166546-0000")
    chunks = [
        res["audio"][i : i + chunk_size]
        for i in range(0, len(res["audio"]), chunk_size)
    ]

    results = []
    for chunk in chunks:
        websocket.send_bytes(chunk)
        res = get_res(websocket)

        if res:
            results.append(json.loads(res))

    assert chunks
    assert results
    websocket.close()
