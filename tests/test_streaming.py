""" test scenario module """

from starlette.testclient import TestClient

import whisperflow.streaming as st
import whisperflow.fast_server as fs


def test_streaming():
    """test hugging face image generation"""
    assert st.run(1) == 2


def test_fast_api():
    """test health api"""
    client = TestClient(fs.app)
    response = client.get("/health")
    assert response.status_code == 200 and bool(response.text)
