""" transcriber """

import os
import torch
import numpy as np
import whisper
from whisper import Whisper


def get_model(file_name="tiny.en.pt") -> Whisper:
    """load models from disk"""
    path = os.path.join(os.path.dirname(__file__), f"./models/{file_name}")
    return whisper.load_model(path).to("cuda" if torch.cuda.is_available() else "cpu")


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
