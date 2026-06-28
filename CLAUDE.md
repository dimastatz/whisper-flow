# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.
See [README.md](README.md) for end-user/usage detail; this file is the agent-facing reference.

## Project overview

Whisper Flow is a real-time, streaming speech-to-text service built on OpenAI Whisper and
served via FastAPI. It splits incoming audio into temporal **tumbling windows** to emit partial
transcripts at sub-500ms latency. Shipped as the Python package `whisperflow` (v1.1.0,
Python 3.8+, developed/tested on 3.12).

## Commands

Everything runs through [run.sh](run.sh). The `-local` target rebuilds `.venv` from scratch;
the other targets assume the venv is already activated (`source .venv/bin/activate`).

| Command | What it does |
|---------|--------------|
| `./run.sh -local` | Fresh `.venv` + install deps + format + lint + tests (first-time setup) |
| `./run.sh -test` | black + pylint + pytest — the inner-loop check before committing |
| `./run.sh -run-server` | uvicorn FastAPI server on port 8181 |
| `./run.sh -benchmark` | Start server, run `tests/benchmark` (LibriSpeech WER/latency), stop |
| `./run.sh -docker` | Build and run the container on port 8888 |

Running a single test (venv activated): `pytest tests/test_streaming.py -v`

## Quality gates — must pass

CI enforces these via [Dockerfile.test](Dockerfile.test). `./run.sh -test` runs the same checks
locally:

- `black whisperflow tests` — formatting (no diffs allowed)
- `pylint --fail-under=9.9 whisperflow tests` — near-perfect lint score required
- `pytest --ignore=tests/benchmark --cov-fail-under=95 --cov whisperflow` — **95% coverage**

Implication: every code change needs accompanying tests to keep coverage ≥95%, and all code
must be black-formatted and pass pylint at 9.9+. Run `./run.sh -test` before considering work
done.

## Architecture & key files

- [whisperflow/transcriber.py](whisperflow/transcriber.py) — Whisper model loading and
  inference: `get_model()`, `transcribe_pcm_chunks()`, `transcribe_pcm_chunks_async()`
- [whisperflow/streaming.py](whisperflow/streaming.py) — tumbling-window streaming logic,
  `TranscribeSession`
- [whisperflow/fast_server.py](whisperflow/fast_server.py) — FastAPI app: WebSocket `/ws`,
  `GET /health`, `POST /transcribe_pcm_chunk`
- [whisperflow/chat_room.py](whisperflow/chat_room.py) — multi-user chat
- [whisperflow/audio/microphone.py](whisperflow/audio/microphone.py) — audio input
- [whisperflow/models/](whisperflow/models/) — bundled `tiny.en.pt` model
- [tests/](tests/) — pytest suite. `tests/benchmark/` and `tests/audio/` are excluded from the
  coverage gate.

## Environment gotchas

- **Python 3.12** preferred — `run.sh` auto-selects `python3.12` when available.
- **`setuptools<70`** pin is required for `openai-whisper` compatibility (see `run.sh`).
- **PortAudio** system dependency is required for PyAudio:
  `brew install portaudio` (macOS) / `apt-get install portaudio19-dev` (Debian/Ubuntu).
- **Audio format**: 16 kHz, mono, 16-bit signed integer (int16) PCM.
- **Ports**: 8181 when run locally, 8888 in Docker.

## Conventions

- Match the existing style; keep modules small and focused.
- Add tests with every code change (the 95% coverage gate enforces this).
- Always run `./run.sh -test` and ensure it is green before finishing.
