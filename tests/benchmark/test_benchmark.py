"""benchamrk"""

import json
import time
import pandas as pd

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
    print(result["is_partial"], round(result["time"], 2), result["data"]["text"])


def test_send_chunks(url="ws://localhost:8181/ws", chunk_size=4096):
    """send chunks"""
    websocket = ws.create_connection(url)
    websocket.settimeout(0.1)

    resource = ut.load_resource("3081-166546-0000")
    chunks = [
        resource["audio"][i : i + chunk_size]
        for i in range(0, len(resource["audio"]), chunk_size)
    ]

    df_result = pd.DataFrame(columns=["is_partial", "latency", "result"])
    for chunk in chunks:
        websocket.send_bytes(chunk)
        res = get_res(websocket)
        if res:
            df_result.loc[len(df_result)] = [
                res["is_partial"],
                round(res["time"], 2),
                res["data"]["text"],
            ]

    attempts = 0
    while attempts < 3:
        res = get_res(websocket)
        if res:
            attempts = 0
            df_result.loc[len(df_result)] = [
                res["is_partial"],
                round(res["time"], 2),
                res["data"]["text"],
            ]
        else:
            attempts += 1
            time.sleep(1)

    pd.set_option("max_colwidth", 800)
    # print(df_result.to_string(justify='left', index=False))
    print("Latency Stats:\n", df_result["latency"].describe())

    actual = df_result.loc[len(df_result) - 1]["result"].lower().strip()
    expected = resource["expected"]["final_ground_truth"].lower().strip()

    error = round(jw.wer(actual, expected), 2)
    assert error < 0.1
    websocket.close()


if __name__ == "__main__":
    print("Starting Whisper-Flow Benchmark")
    test_send_chunks()
    print("Whisper-Flow Benchmark Completed")
