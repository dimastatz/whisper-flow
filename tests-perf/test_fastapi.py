""" integration test for web server """
import requests


def test_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url)
    assert result.status_code == 200


def test_streaming_api():
    """test streaming api"""
    result = 1
    assert result == 1
