"""benchamrk"""

import json
import time
import requests
import jiwer as jw
import websocket as ws
import tests.utils as ut


def test_health(url="http://localhost:8181/health"):
    """basic test"""
    result = requests.get(url=url, timeout=1)
    assert result.status_code == 200


def get_res(websocket):
    """try read with timout"""
    try:
        result = json.loads(websocket.recv())
        print_result(result)
        return result
    except ws.WebSocketTimeoutException:
        return {}


def print_result(result: dict):
    """print result and execution time"""
    formatted_time = "{:.2f}".format(result["time"])
    print(result["is_partial"], result["data"]["text"], formatted_time)


def test_send_chunks(url="ws://localhost:8181/ws", chunk_size=4096):
    """send chunks"""
    websocket = ws.create_connection(url)
    websocket.settimeout(0.1)

    resource = ut.load_resource("3081-166546-0000")
    chunks = [
        resource["audio"][i : i + chunk_size]
        for i in range(0, len(resource["audio"]), chunk_size)
    ]

    results = []
    for chunk in chunks:
        websocket.send_bytes(chunk)
        res = get_res(websocket)
        if res:
            results.append(res)

    attempts = 0
    while attempts < 3:
        res = get_res(websocket)
        if res:
            attempts = 0
            results.append(res)
        else:
            attempts += 1
            time.sleep(1)

    item = [x for x in results if not x["is_partial"]][-1:][0]

    actual = item["data"]["text"].lower().strip()
    expected = resource["expected"]["final_ground_truth"].lower().strip()

    error = jw.wer(actual, expected)
    assert error < 0.1
    websocket.close()

    min_lt = min([x["time"] for x  in results])
    max_lt = min([x["time"] for x  in results])
    avg_lt = min([x["time"] for x  in results])
    print(f"Benchmark Results WER={error}, Latency Min={min_lt} Max={max_lt} Avg={avg_lt}")


if __name__ == "__main__":
    print("Starting Whisper-Flow Benchmark")
    test_send_chunks()
    print("Whisper-Flow Benchmark Completed")
