""" test utils class """

import os
import json
from starlette.testclient import TestClient
import whisperflow.fast_server as fs


def load_resource(name: str) -> dict:
    "load resource"
    result = {}
    current_path = os.path.dirname(__file__)
    resource_name = os.path.join(current_path, f"./resources/{name}")

    with open(resource_name + ".wav", "br") as file:
        result["audio"] = file.read()

    with open(resource_name + ".json", "r", encoding="utf-8") as file:
        result["expected"] = json.load(file)

    return result


def test_fast_api():
    """test health api"""
    with TestClient(fs.app) as client:
        response = client.get("/health")
        assert response.status_code == 200 and bool(response.text)
