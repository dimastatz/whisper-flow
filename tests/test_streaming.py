""" test scenario module """
import pytest
from starlette.testclient import TestClient

import whisperflow.streaming as st
import whisperflow.fast_server as fs


def test_streaming():
    """test hugging face image generation"""
    assert st.run(1) == 2


def test_fast_api():
    """test health api"""
    with TestClient(fs.app) as client:
        response = client.get("/health")
        assert response.status_code == 200 and bool(response.text)


@pytest.mark.asyncio
async def test_ws():
    """test health api"""
    client = TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, world!")
        data = websocket.receive_bytes()
        assert data == b"Hello, world!"
