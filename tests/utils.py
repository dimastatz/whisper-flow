""" test utils class """

import os
import json


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
