""" test transcriber """

from jiwer import wer
from tests.utils import load_resource

import whisperflow.transcriber as tr


def test_load_model():
    """test hugging face image generation"""
    model = tr.get_model()
    assert model is not None

    resource = load_resource("3081-166546-0000")

    result = tr.transcribe_pcm_chunks(model, [resource["audio"]])
    expected = resource["expected"]["final_ground_truth"]

    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1
