""" transcriber """

import os
import asyncio
import threading
from typing import Optional

import torch
import numpy as np

import whisper
from whisper import Whisper

from whisperflow import config


models = {}
_models_lock = threading.Lock()


def resolve_model_path(file_name: str) -> str:
    """validate a model name and return its path inside the models dir"""
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    path = os.path.normpath(os.path.join(models_dir, file_name))
    if os.path.dirname(path) != models_dir:
        raise ValueError(f"invalid model name: {file_name}")
    if not os.path.isfile(path):
        raise ValueError(f"unknown model: {file_name}")
    return path


def get_model(file_name: Optional[str] = None) -> Whisper:
    """load a model from disk, caching one shared instance (thread-safe)"""
    name = file_name or config.DEFAULT_MODEL
    if name not in models:
        path = resolve_model_path(name)
        with _models_lock:
            if name not in models:
                models[name] = whisper.load_model(path).to(
                    "cuda" if torch.cuda.is_available() else "cpu"
                )
    return models[name]


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


async def transcribe_pcm_chunks_async(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks async"""
    return await asyncio.get_running_loop().run_in_executor(
        None, transcribe_pcm_chunks, model, chunks, lang, temperature, log_prob
    )
