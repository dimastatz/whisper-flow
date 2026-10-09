""" transcriber """

import os
import copy
import queue
import asyncio
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Iterator, Optional, Union

import torch
import numpy as np

import whisper
from whisper import Whisper

from whisperflow import config


models = {}
_models_lock = threading.Lock()
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# transcriptions run here rather than on the default executor, which also serves
# model loading and other blocking work
EXECUTOR = ThreadPoolExecutor(
    max_workers=config.TRANSCRIBE_WORKERS, thread_name_prefix="transcribe"
)


class ModelPool:  # pylint: disable=too-few-public-methods
    """replicas of one model; each replica runs one transcription at a time

    A Whisper model is not safe to use from two threads at once: decoding installs
    kv-cache hooks on the model's layers, so concurrent calls corrupt each other's
    output or crash. Sessions share the pool and wait for a free replica.
    """

    def __init__(self, model: Whisper, replicas: int = 1) -> None:
        """ctor: the model plus replicas - 1 deep copies"""
        self.replicas = [model] + [copy.deepcopy(model) for _ in range(replicas - 1)]
        self.free = queue.Queue()
        for replica in self.replicas:
            self.free.put(replica)

    @contextmanager
    def acquire(self) -> Iterator[Whisper]:
        """borrow a replica, blocking until one is free"""
        replica = self.free.get()
        try:
            yield replica
        finally:
            self.free.put(replica)


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


def get_model(file_name: Optional[str] = None) -> ModelPool:
    """load a model from disk into a pool of WF_MODEL_REPLICAS replicas (cached)"""
    name = file_name or config.DEFAULT_MODEL
    if name not in models:
        path = resolve_model_path(name)
        with _models_lock:
            if name not in models:
                model = whisper.load_model(path).to(
                    "cuda" if torch.cuda.is_available() else "cpu"
                )
                models[name] = ModelPool(model, max(1, config.MODEL_REPLICAS))
    return models[name]


def transcribe_pcm_chunks(  # pylint: disable=too-many-arguments
    model: Union[ModelPool, Whisper],
    chunks: list,
    lang="en",
    temperature=0.1,
    log_prob=-0.5,
    *,
    prompt=None,
    word_timestamps=False,
) -> dict:
    """transcribes pcm chunks list; a pool is borrowed from for the call"""
    if isinstance(model, ModelPool):
        with model.acquire() as replica:
            return transcribe_pcm_chunks(
                replica,
                chunks,
                lang,
                temperature,
                log_prob,
                prompt=prompt,
                word_timestamps=word_timestamps,
            )
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
        word_timestamps=word_timestamps,
    )


async def transcribe_pcm_chunks_async(  # pylint: disable=too-many-arguments
    model: Union[ModelPool, Whisper],
    chunks: list,
    lang="en",
    temperature=0.1,
    log_prob=-0.5,
    *,
    prompt=None,
    word_timestamps=False,
) -> dict:
    """transcribes pcm chunks async, on the transcription executor"""
    run = partial(transcribe_pcm_chunks, prompt=prompt, word_timestamps=word_timestamps)
    return await asyncio.get_running_loop().run_in_executor(
        EXECUTOR, run, model, chunks, lang, temperature, log_prob
    )
