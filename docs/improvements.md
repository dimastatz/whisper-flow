# WhisperFlow: Improvements Map

An engineering backlog of things to **fix or add** to make WhisperFlow better, grounded in an
audit of the actual source, packaging, tests, CI, and docs. Items are independent — each can be
its own small PR. Run them as iterations via the
[monetization-feedback-loop.md](monetization-feedback-loop.md) cadence if useful.

**Priority legend:**
- **P0** — correctness or security; can bite in production or breaks today.
- **P1** — production-readiness, observability, and test/CI quality.
- **P2** — polish, hygiene, and developer experience.

> ⚡ **Quick wins (highest value-to-effort — do this week):** version-mismatch fix · remove the
> stray line in `monetizations.md` · README Docker port fix · `find_packages()` in `setup.py` ·
> clean up the `sessions` leak · share one model instance instead of per-connection.

---

## P0 — Correctness & security

| # | What | Why | Where |
|---|------|-----|-------|
| 1 | **Share one model instance** server-wide; pre-load at startup via FastAPI lifespan instead of `ts.get_model()` per connection | First connection pays full model-load latency; needless memory churn under concurrency | [fast_server.py:36](../whisperflow/fast_server.py#L36), [transcriber.py](../whisperflow/transcriber.py) |
| 2 | **Clean up `sessions[session.id]`** on disconnect | Sessions are added but never removed → unbounded memory growth (leak) on a long-running server | [fast_server.py:48](../whisperflow/fast_server.py#L48) |
| 3 | **Synchronize the global `models` cache** (lock or `functools.lru_cache`) | `models = {}` has a check-then-load race; two concurrent first-connects can double-load | [transcriber.py:16-23](../whisperflow/transcriber.py#L16-L23) |
| 4 | **Validate `model_name`** against an allowlist | Request-supplied name is used to load a file unchecked → path-traversal / arbitrary-file risk | [fast_server.py:25](../whisperflow/fast_server.py#L25) |
| 5 | **Add auth + request size limits + basic rate limiting** to `/ws` and `/transcribe_pcm_chunk` | Endpoints are fully open: anyone can submit audio; large uploads read into memory → DoS/OOM | [fast_server.py](../whisperflow/fast_server.py) |
| 6 | **Replace `assert` used as control flow** with an explicit check | `assert` is stripped under `python -O`; silently disables the check in optimized runs | [chat_room.py:41](../whisperflow/chat_room.py#L41) |
| 7 | **Bound the streaming window** (max size / timeout) and wrap the transcription loop in try/except with logging | Window list grows until a close condition that may never fire; a transcriber exception kills the session silently | [streaming.py](../whisperflow/streaming.py) |

## P0 — Packaging & dependencies (currently broken)

| # | What | Why | Where |
|---|------|-----|-------|
| 8 | **Fix packaging**: use `find_packages()` (ships `whisperflow.audio`), include the model via `package_data`/`MANIFEST.in`, drop the bogus `static/*`, add classifiers — or migrate to `pyproject.toml` | `py_modules=['whisperflow']` won't package the `audio` subpackage; `package_data={'': ['static/*']}` points at a non-existent dir; `pkg_resources` is deprecated | [setup.py](../setup.py) |
| 9 | **Fix the version mismatch** — derive the wheel filename from `__version__` | `-test-package` installs `whisperflow-0.1.0-...whl` but the package is `1.1.0`, so the target is broken | [run.sh:76](../run.sh#L76), [__init__.py](../whisperflow/__init__.py) |
| 10 | **Split runtime vs dev/test deps** (extras or `requirements-dev.txt`); verify/fix `pandas==3.0.1`; pin `torch`; drop unused runtime deps (`httpx`, `websocket-client`, `pandas`) | One file mixes `black`/`pylint`/`pytest` with runtime; installing the library drags in the whole test toolchain; `torch` (the heavy core dep) is only transitive/unpinned | [requirements.txt](../requirements.txt) |

## P1 — Production readiness & observability

- **Real health/readiness:** structured `/health` + a `/ready` that reports model-loaded state; **graceful shutdown** that drains active sessions (FastAPI lifespan). *([fast_server.py](../whisperflow/fast_server.py))*
- **Logging & metrics:** structured logging + counters for active connections, transcription latency, and errors — today there's no observability into a real-time path.
- **Transcription timeout / cancellation** so a hung inference can't block a session indefinitely. *([streaming.py](../whisperflow/streaming.py))*
- **Configuration via env vars** instead of hardcoded magic numbers: model name, ports, window/silence params, sample rate, chunk size. *([transcriber.py](../whisperflow/transcriber.py), [streaming.py](../whisperflow/streaming.py), [audio/microphone.py](../whisperflow/audio/microphone.py))*
- **Unblock the event loop:** move blocking PyAudio `read`/`write` to `run_in_executor`, and guarantee device cleanup with try/finally. *([audio/microphone.py](../whisperflow/audio/microphone.py))*

## P1 — Testing & CI

- **Move pytest/coverage config** out of `run.sh` into `pyproject.toml` / `pytest.ini` (thresholds, ignore patterns, markers) so it's discoverable and IDE-friendly.
- **Add error-path tests:** invalid model name, malformed audio, disconnect mid-stream, and the `fast_server` branches currently hidden behind `# pragma: no cover`.
- **Make CI run real steps:** lint + format + tests as visible CI jobs (not only a Docker build), a **Python version matrix** (3.8–3.12, since `setup.py` claims `>=3.8`), dependency caching, and coverage upload.
- **Dependabot for `pip`** (it currently watches only devcontainers); **consolidate** the ~92%-identical `Dockerfile` / `Dockerfile.test` (multi-stage or a build arg).
- **Release automation:** a tag-gated publish-to-PyPI workflow.

## P2 — Repo hygiene

- **Stop committing the 72 MB `whisperflow/models/tiny.en.pt`** — download it on first use, or use Git LFS / a fetch step. It bloats every clone and the history. *(verified tracked via `git ls-files`)*
- Ensure `.venv*`, `dist/`, `build/`, `*.egg-info/` are never tracked.
- **Remove the stray junk line** ("Is this submission being made to claim treaty benefits?") at [docs/monetizations.md:47](monetizations.md).

## P2 — Docs & developer experience

- **Fix the README Docker port:** the manual `docker run` shows `-p 8181:8181` but `run.sh -docker` maps `8888:8888`. *([README.md](../README.md))*
- **Add project-health files:** `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, and `.github/` issue + PR templates. (LICENSE/MIT already present.)
- **Add a browser/JS WebSocket demo** — only a Python mic client exists ([tests/examples/mic_transcribe.py](../tests/examples/mic_transcribe.py)). A small HTML page lowers the "try it" barrier dramatically.
- **Add a technical doc** (architecture + API reference) under `docs/` — current docs are business/strategy only.
- **Fix the devcontainer:** it defaults to Python **3.10** but the project wants **3.12**; uncomment `postCreateCommand` to auto-install deps; forward port 8181. Expand `.vscode/settings.json` beyond the pytest stub.
- **Discoverability:** add CI/PyPI/license badges + an output screenshot to the README; set GitHub repo topics (`speech-recognition`, `whisper`, `streaming`, `real-time-transcription`, `fastapi`).

---

## Suggested sequencing

1. **P0 quick wins first** (the ⚡ list) — small, high-leverage, mostly independent.
2. **Rest of P0** — correctness/security and the broken packaging.
3. **P1** — production-readiness, then tests/CI (CI improvements make every later change safer).
4. **P2** — hygiene and docs/DX polish.

Each item is independent and sized for a single small PR — pick one per iteration, verify with
`./run.sh -test`, and keep the quality gates (black, pylint ≥9.9, 95% coverage) green.
