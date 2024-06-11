""" test transcriber """

import os
import whisperflow.transcriber as tr


def test_load_model():
    """test hugging face image generation"""
    model = tr.get_model()
    assert model is not None

    path = os.path.join(os.path.dirname(__file__), "./resources/3081-166546-0000.wav")

    with open(path, "br") as file:
        content = file.read()

    text = tr.transcribe_pcm_chunks(model, [content])
    assert text
