""" runtime configuration sourced from environment variables """

import os


def get_int(name: str, default: int) -> int:
    """read an int env var, falling back to default on missing/invalid"""
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def get_float(name: str, default: float) -> float:
    """read a float env var, falling back to default on missing/invalid"""
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


# audio capture/playback
SAMPLE_RATE = get_int("WF_SAMPLE_RATE", 16000)
CHUNK_SIZE = get_int("WF_CHUNK_SIZE", 1024)
SILENCE_THRESHOLD = get_int("WF_SILENCE_THRESHOLD", 500)

# model / transcription
DEFAULT_MODEL = os.environ.get("WF_MODEL", "tiny.en.pt")
TRANSCRIBE_TIMEOUT = get_float("WF_TRANSCRIBE_TIMEOUT", 30.0)
MAX_WINDOW_CHUNKS = get_int("WF_MAX_WINDOW_CHUNKS", 1000)

# server limits / auth
MAX_UPLOAD_BYTES = get_int("WF_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
MAX_SESSIONS = get_int("WF_MAX_SESSIONS", 128)
API_KEY = os.environ.get("WF_API_KEY") or None
