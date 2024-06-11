""" transcriber """

import numpy as np
from whisper import Whisper


def transcribe_pcm_chunks(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks list"""
    arr = (
        np.frombuffer(b"".join(chunks), np.int16).flatten().astype(np.float32) / 32768.0
    )
    return model.transcribe(
        arr,
        fp16=False,
        language=lang,
        logprob_threshold=log_prob,
        temperature=temperature,
    )
