""" integration test for web server """
from pathlib import Path

import requests
from websocket import create_connection


def test_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url, timeout=1)
    assert result.status_code == 200


def test_streaming_api(url="ws://localhost:8000/ws", chunk_size=4096):
    """test streaming api"""
    folder = Path(__file__).resolve().parents[1]
    assert folder
    assert chunk_size

    web_socket = create_connection(url)
    web_socket.settimeout(0.01)
    assert web_socket
