# WhisperFlow in VS Code

A plan for a VS Code extension that streams microphone audio to a WhisperFlow server and inserts
transcripts into the editor. This document covers positioning, the two architecture decisions that
constrain everything else, the server-side work that must land first, and a feature roadmap.

**Status:** implemented. The extension is [whisper-code](https://github.com/dimastatz/whisper-code)
(see its `docs/specs`). The §4 prerequisites have all landed; §5 lists what remains on the
extension side.

---

## 1. Goal and positioning

Voice input for developers: dictate prose into Markdown/comments, and speak into AI chat panels
instead of typing long prompts.

Be clear-eyed about what already exists:

| Competitor | What it does | Why it matters |
|---|---|---|
| **VS Code Speech** (`ms-vscode.vscode-speech`, Microsoft) | On-device dictation wired into Copilot Chat, free | "A mic button in VS Code" is not a wedge on its own |
| **Wispr Flow, superwhisper** | OS-level dictation, works in every app | Better default for generic dictation |
| **macOS / Windows built-in dictation** | Free, zero setup | Sets the floor for quality expectations |

The defensible angles for WhisperFlow — pick and design for these rather than shipping a generic
mic button:

- **Self-hosted / air-gapped.** Audio never leaves infrastructure you control. The only option on
  this list that can satisfy a compliance review.
- **Remote GPU.** Point the extension at a server running a large model; the laptop stays cool.
  Competitors are pinned to on-device models.
- **Custom vocabulary.** Bias toward a codebase's identifiers, product names, and jargon.
- **Linux**, where the OS-level tools are weakest.

---

## 2. Decision: audio capture via sidecar, not webview

The extension host is Node — there is no `getUserMedia`. Two options:

| Approach | Verdict |
|---|---|
| **Webview** — an iframe that can request mic permission | **Rejected.** A webview takes focus when shown, so the cursor leaves the editor. That is disqualifying for dictate-at-cursor, the primary use case. Acceptable only for a chat-panel-only UX. |
| **Sidecar process** — spawn a recorder, pipe raw PCM over the WebSocket | **Chosen.** Works while the editor keeps focus, works headless, works over Remote-SSH. |

The sidecar is largely already written: [audio/microphone.py](../whisperflow/audio/microphone.py)
captures exactly the format the server expects — 16 kHz, mono, int16, per
[config.py:23-24](../whisperflow/config.py#L23-L24). Ship the Python client as the recorder, or
reimplement in Node (`node-record-lpcm16` / sox) to avoid a Python dependency on the client side.

**Spike this first.** Everything downstream depends on capture working.

## 3. Decision: the extension lives in a separate repo

**Whisper Code** — `dimastatz/whisper-code`, extension id `whisper-code` — not a subdirectory here.
The distinct name avoids confusion with the Wispr Flow dictation product and signals the
developer/code niche; WhisperFlow remains the name of the server it speaks to.

| Reason | Evidence |
|---|---|
| One tag namespace, two registries | [publish.yml](../.github/workflows/publish.yml) already claims `v*` tags for PyPI; Marketplace releases want tags too |
| Docker build context pollution | [Dockerfile.test](../Dockerfile.test) does `COPY . .` — `node_modules/` would land in the image and bust layer caching on every extension commit |
| Accidental PyPI shipping | `find_packages()` + `include_package_data=True` in [setup.py](../setup.py) publishes anything under `whisperflow/` |
| Mismatched quality gates | CI here is `black` / `pylint --fail-under=9.9` / `pytest --cov whisperflow` — a TS toolchain makes that contract ambiguous |
| Licensing | Keeps a commercial license on the extension without touching the MIT server |
| Marketplace page | `vsce` renders the root `README.md` as the extension listing |

**The tradeoff:** no atomic commits when the wire protocol changes. Mitigated by treating the
protocol as a versioned contract owned by this repo — see §4.

---

## 4. Server-side prerequisites

These must land in WhisperFlow before the extension can offer a decent UX. Each is an independent
PR; keep the gates green per [CLAUDE.md](../CLAUDE.md).

Done: 1 (#39), 2 (#43), 3 (#40), 4 (committed prefix), 5 (#42), 6 (model replicas).

| # | What | Why | Where |
|---|------|-----|-------|
| 1 | **Control frames + finalize-on-stop.** Accept JSON control messages (`start` with model/language, `flush`, `stop`) alongside binary audio; on stop, drain the queue and emit a final result | Today `/ws` only reads bytes, and `stop()` just flips a flag — queued tail audio is dropped and the last partial never becomes final. **Losing the end of the last sentence makes dictation unusable** | [fast_server.py:111](../whisperflow/fast_server.py#L111), [streaming.py:108-111](../whisperflow/streaming.py#L108-L111) |
| 2 | **VAD-driven endpointing.** Finalize on a silence threshold rather than on repeated text | `should_close_segment` fires when text is identical across two cycles, but Whisper flips punctuation between passes, so it fires late or never. `is_silent` already exists but is unused by the server path | [streaming.py:85-89](../whisperflow/streaming.py#L85-L89), [audio/microphone.py:62](../whisperflow/audio/microphone.py#L62) |
| 3 | **`PROTOCOL_VERSION` + `docs/protocol.md`.** A constant beside `__version__`, surfaced as a `protocol_version` key on `/ready`, plus the wire contract written down | Lets the extension pre-flight over plain HTTP and fail loudly on a version mismatch — the mitigation for the two-repo split | [\_\_init\_\_.py](../whisperflow/__init__.py), [fast_server.py:58-66](../whisperflow/fast_server.py#L58-L66) |
| 4 | **Incremental decoding** (or at least a committed-prefix scheme) | Every cycle re-transcribes the whole growing window, so cost rises with utterance length and partials rewrite already-emitted words | [streaming.py:62](../whisperflow/streaming.py#L62) |
| 5 | **Model selection per session**, beyond the bundled `tiny.en.pt` | `tiny.en` is rough on code dictation (identifiers, camelCase, symbols). Remote-GPU positioning requires larger models | [transcriber.py](../whisperflow/transcriber.py) |
| 6 | **Per-session concurrency.** `run_in_executor(None, ...)` on the default pool with one shared model | Fine for one user, poor for a shared team server | [transcriber.py:65-67](../whisperflow/transcriber.py#L65-L67) |

### Known constraints to document, not necessarily fix

- **Partials are not monotonic.** Clients must hold a *pending range* and replace it on each
  partial, committing only when `is_partial` is `false`. Never append. This shapes the extension's
  insertion logic and is painful to retrofit — design for it from day one.
- **`MAX_WINDOW_CHUNKS = 1000`** caps a window at roughly 64 s at 16 kHz and truncates the *start*
  of a long dictation mid-sentence. *([config.py:30](../whisperflow/config.py#L30))*
- Close codes already in use: `1008` (auth failure), `1013` (at `MAX_SESSIONS`).

---

## 5. Extension roadmap

### MVP

| Feature | Notes |
|---|---|
| Sidecar recorder → `/ws` streaming | The §2 spike, productionized |
| Toggle dictation via command + keybinding | One hotkey to start/stop; no modal UI |
| Insert at cursor with pending-text decoration | Partial shown dimmed in a replaceable range; committed on final |
| Status bar mic indicator | Idle / recording / transcribing / error |
| Server settings | URL, `x-api-key`, model, language |
| Version handshake | `GET /ready`, compare `protocol_version`, warn clearly on mismatch |

### Post-MVP

| Feature | Notes |
|---|---|
| Dictate into AI chat input | Copilot Chat, Claude Code, and similar panels — likely the highest-value target |
| Command mode | "new line", "comma", "undo that" — Whisper's punctuation is inconsistent for code |
| Custom vocabulary | Prompt biasing from workspace symbols; the clearest differentiator |
| Managed server lifecycle | Auto-start a local server, or one-click connect to a remote GPU box |
| Transcribe an audio file in the workspace | Reuses `POST /transcribe_pcm_chunk` |

### Deliberately not in scope

- **The proposed VS Code speech-provider API** (which would let an extension supply STT to
  Copilot's own mic button) is insiders-only until it stabilizes. Attractive later; not a
  foundation to build on.
- Multi-language UI, translation, and speaker diarization.

---

## 6. Sequencing

1. **Capture spike** — sidecar mic → `/ws` → log partials to the debug console. Perhaps 200 lines.
   If latency feels bad here with `tiny.en`, stop and fix the server before building UI.
2. **Server prerequisites 1 and 3** (control frames + protocol contract) — the extension's whole
   insertion UX depends on a reliable final.
3. **MVP extension** in the new repo.
4. **Server prerequisites 2, 4, 5** — quality and latency, informed by real dictation use.
5. **Post-MVP features**, prioritized by whichever differentiator from §1 you commit to.

**Quality bar for the spike:** dictate `const userId equals await fetchUser open paren id close
paren` and see what comes back. If code-shaped speech is unusable at `tiny.en`, model selection
(prerequisite 5) moves ahead of the MVP.
