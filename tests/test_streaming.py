""" test scenario module """

import whisperflow.streaming as st


def test_streaming():
    """test hugging face image generation"""
    assert st.run(1) == 2
