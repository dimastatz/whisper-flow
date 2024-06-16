""" test transcriber """

from jiwer import wer
import tests.utils as ut

import whisperflow.fast_server as fr
import whisperflow.transcriber as tr


def test_load_model():
    """test load model from disl"""
    model = tr.get_model()
    assert model is not None

    resource = ut.load_resource("3081-166546-0000")

    result = tr.transcribe_pcm_chunks(model, [resource["audio"]])
    expected = resource["expected"]["final_ground_truth"]

    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1


def test_transcribe_chunk():
    """test transcribe pcm chunk"""
    resource = ut.load_resource("3081-166546-0000")
    client = ut.TestClient(fr.app)
    response = client.get("/health")
    assert response.status_code == 200
