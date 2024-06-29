"""benchamrk"""
import requests


def test_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url, timeout=1)
    assert result.status_code == 200
