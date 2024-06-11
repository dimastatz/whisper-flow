""" test transcriber """

import whisperflow.transcriber as tr


def test_load_model():
    """test hugging face image generation"""
    model = tr.get_model()
    assert model is not None
