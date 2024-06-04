""" test scenario module """

import whisper_flow.streaming as st


def test_streaming():
    """test hugging face image generation"""
    assert st.run(1) == 2
