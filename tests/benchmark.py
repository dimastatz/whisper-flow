"""" benchmark """
from pathlib import Path

import requests
import websocket as ws


def send_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url, timeout=1)
    assert result.status_code == 200


def send_chunks(url="ws://localhost:8181/ws", chunk_size=4096):
    """ send chunks """
    folder = Path(__file__).resolve().parents[1]
    assert folder
    assert chunk_size

    websocket = ws.create_connection(url)
    websocket.settimeout(0.1)
    websocket.close()


if __name__ == "__main__":
    print("Starting benchmark")
    send_health()
    send_chunks()
    print("Ending benchmark")
