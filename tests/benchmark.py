"""" benchmark """
import os
import json
from pathlib import Path
import websocket as ws


def send_chunks(url="ws://localhost:8181/ws", chunk_size=4096):
    """send chunks"""
    folder = Path(__file__).resolve().parents[1]
    assert folder
    assert chunk_size

    websocket = ws.create_connection(url)
    websocket.settimeout(0.1)

    res = load_resource("3081-166546-0000")
    chunks = [
        res["audio"][i : i + chunk_size]
        for i in range(0, len(res["audio"]), chunk_size)
    ]

    print(len(chunk_size))

    websocket.close()


def load_resource(name: str) -> dict:
    "load resource"
    result = {}

    with open(get_resource_path(name, "wav"), "br") as file:
        result["audio"] = file.read()

    with open(get_resource_path(name, "json"), "r", encoding="utf-8") as file:
        result["expected"] = json.load(file)

    return result


def get_resource_path(name: str, extension: str) -> str:
    "get resources path"
    current_path = os.path.dirname(__file__)
    path = os.path.join(current_path, f"./resources/{name}")
    return f"{path}.{extension}"


if __name__ == "__main__":
    print("Starting benchmark")
    send_chunks()
    print("Ending benchmark")
