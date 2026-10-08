# Whisper Flow wire protocol

**Protocol version: 1.** `GET /ready` reports it as `protocol_version`. Clients should check it
before opening a session and refuse to run on a version they don't know. Any breaking change to
this document bumps `PROTOCOL_VERSION` in [whisperflow/\_\_init\_\_.py](../whisperflow/__init__.py).
Additive changes (new optional fields or messages) do not.

## HTTP

### `GET /ready`

```json
{
  "status": "ok",
  "version": "1.2.1",
  "protocol_version": 1,
  "models": ["tiny.en.pt"],
  "model_loaded": true,
  "active_sessions": 0
}
```

`models` lists the model files a session may choose (see [Models](#models)).

### `POST /transcribe_pcm_chunk`

Multipart form: `model_name` (required), `files` (one PCM file, required), and `prompt`
(optional vocabulary prompt). It returns Whisper's result. An unknown model or an invalid prompt
returns `400`, and an upload over `WF_MAX_UPLOAD_BYTES` returns `413`.

## WebSocket `/ws`

### Authentication and admission

If the server sets `WF_API_KEY`, send it in the `x-api-key` header, on both HTTP and WebSocket.

| Close code | Meaning |
| :--------- | :------ |
| `1008` | Missing or wrong API key |
| `1013` | Server is at `WF_MAX_SESSIONS` |
| `4000` | `start` frame with invalid options; the close reason says which |

### Client → server

**Binary frames** carry audio: 16 kHz, mono, signed 16-bit little-endian PCM. Frames may be any
length; 1024 samples (2048 bytes) per frame is the default the bundled clients use.

**Text frames** carry JSON control messages:

| Message | Effect |
| :------ | :----- |
| `{"type": "start", "model": "tiny.en.pt", "language": "en", "prompt": "useMemo getUserById"}` | Session options. Every field is optional; send it before any audio |
| `{"type": "flush"}` | Transcribe all audio sent so far and send it as a final result |
| `{"type": "stop"}` | Same as `flush`, then close the socket normally (`1000`) |

`start` options:

- `model`: a name from `GET /ready` `models`. The default is the server's `WF_MODEL`.
- `language`: a Whisper language code such as `en` or `de`. The default is `en`. English-only
  (`*.en`) models ignore it.
- `prompt`: vocabulary passed to Whisper as `initial_prompt`, to bias spelling of identifiers,
  product names and jargon. At most `WF_MAX_PROMPT_CHARS` characters (default 800; Whisper only
  uses roughly the last 224 tokens). Omit it or send `""` for no prompt.

A malformed or unknown control message gets `{"type": "error", "message": "invalid control"}`
and the session continues. Clients that send only binary frames work without any control
messages. Closing the socket without `stop` discards audio not yet transcribed.

### Server → client

```json
{ "is_partial": true, "data": { "text": " Reality is created", "segments": [], "language": "en" }, "time": 412.5 }
```

- `data` is Whisper's result; `text` is the transcript of the current segment so far.
- `time` is the processing time of this result in milliseconds.
- **Partials are not monotonic.** Each partial replaces the previous one for the same segment;
  words can change or disappear. Clients must hold a pending range and replace it, never append.
  Commit text only when `is_partial` is `false`.
- After a final, the next result belongs to a new segment.

### When a segment becomes final

A segment is sent with `is_partial: false` when the first of these happens:

1. **Silence.** Speech is followed by `WF_SILENCE_MS` (default 600) of silence. A chunk is silent
   when every sample is below `WF_SILENCE_THRESHOLD` (default 500). The final arrives within one
   transcription cycle of the pause.
2. **Stable text.** Two consecutive transcriptions are equal, ignoring case and punctuation.
3. **Window cap.** The segment reaches `WF_MAX_WINDOW_CHUNKS` frames (default 1000, about 64 s at
   1024-sample frames). It is sent as a final and a new segment starts, so no audio is dropped.
4. **`flush` / `stop`** from the client.

Audio that contains only silence is not transcribed. Before speech starts, at most
`WF_SILENCE_MS` of lead-in audio is kept. Set `WF_SILENCE_THRESHOLD=0` to treat all audio as
speech, for example with very quiet input.

## Models

The server loads models from [whisperflow/models/](../whisperflow/models/). Only `tiny.en.pt` is
bundled. To add one, download a Whisper checkpoint (for example `base.en.pt` or `small.en.pt` from
the URLs in `whisper._MODELS`) into that directory. It then appears in `GET /ready` `models`.
Models load on first use and stay in memory.
