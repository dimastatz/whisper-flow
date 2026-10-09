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
SILENCE_MS = get_int("WF_SILENCE_MS", 600)

# model / transcription
DEFAULT_MODEL = os.environ.get("WF_MODEL", "tiny.en.pt")
TRANSCRIBE_TIMEOUT = get_float("WF_TRANSCRIBE_TIMEOUT", 30.0)
MAX_WINDOW_CHUNKS = get_int("WF_MAX_WINDOW_CHUNKS", 1000)
MAX_PROMPT_CHARS = get_int("WF_MAX_PROMPT_CHARS", 800)
# replicas of each model; each runs one transcription at a time (memory grows per replica)
MODEL_REPLICAS = get_int("WF_MODEL_REPLICAS", 1)
TRANSCRIBE_WORKERS = get_int("WF_TRANSCRIBE_WORKERS", 8)
# commit words that two consecutive partials agree on and drop their audio (see streaming.py)
COMMIT_PREFIX = get_int("WF_COMMIT_PREFIX", 1) != 0
# start committing once the uncommitted window is this long
COMMIT_AFTER_MS = get_int("WF_COMMIT_AFTER_MS", 4000)
# never commit words ending within this much of the window's end
COMMIT_MARGIN_MS = get_int("WF_COMMIT_MARGIN_MS", 1000)

# server limits / auth
MAX_UPLOAD_BYTES = get_int("WF_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
MAX_SESSIONS = get_int("WF_MAX_SESSIONS", 128)
API_KEY = os.environ.get("WF_API_KEY") or None
