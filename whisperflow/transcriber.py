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
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def list_models() -> list:
    """names of the model files available in the models dir"""
    return sorted(name for name in os.listdir(MODELS_DIR) if name.endswith(".pt"))


def check_prompt(prompt: Optional[str]) -> Optional[str]:
    """validate a vocabulary prompt; empty means no prompt"""
    if prompt is None or prompt == "":
        return None
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    if len(prompt) > config.MAX_PROMPT_CHARS:
        raise ValueError(f"prompt longer than {config.MAX_PROMPT_CHARS} characters")
    return prompt


def resolve_model_path(file_name: str) -> str:
    """validate a model name and return its path inside the models dir"""
    path = os.path.normpath(os.path.join(MODELS_DIR, file_name))
    if os.path.dirname(path) != MODELS_DIR:
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


def transcribe_pcm_chunks(  # pylint: disable=too-many-arguments
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5, prompt=None
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
        initial_prompt=prompt,
    )


async def transcribe_pcm_chunks_async(  # pylint: disable=too-many-arguments
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5, prompt=None
) -> dict:
    """transcribes pcm chunks async"""
    return await asyncio.get_running_loop().run_in_executor(
        None, transcribe_pcm_chunks, model, chunks, lang, temperature, log_prob, prompt
    )
