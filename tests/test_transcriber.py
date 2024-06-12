""" test transcriber """

import os
import json
from jiwer import wer
import whisperflow.transcriber as tr


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


def test_load_model():
    """test hugging face image generation"""
    model = tr.get_model()
    assert model is not None

    resource = load_resource("3081-166546-0000")

    result = tr.transcribe_pcm_chunks(model, [resource["audio"]])
    expected = resource["expected"]["final_ground_truth"]

    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1
