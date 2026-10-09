""" tests for the committed-prefix scheme and the model pool """

import asyncio
import threading
import time
from queue import Queue

import pytest

import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.transcriber as ts
import whisperflow.fast_server as fs


SPEECH = b"\xff\x7f" * 800  # 50 ms at full scale


def numbered(index: int) -> bytes:
    """50 ms of loud audio whose first byte carries `index`"""
    return bytes([index, 0x7F]) * 800


def numbered_words(window: list) -> dict:
    """fake transcription: one word per chunk, named by the chunk's index"""
    return words_result([f"w{chunk[0]}" for chunk in window])


def words_result(names: list, step=0.05) -> dict:
    """a Whisper-like result with one word per `step` seconds"""
    words = [
        {"word": f" {name}", "start": i * step, "end": (i + 1) * step}
        for i, name in enumerate(names)
    ]
    return {
        "text": "".join(word["word"] for word in words),
        "segments": [{"words": words}],
    }


def speech_segment(chunks: int) -> st.Segment:
    """a segment holding `chunks` 50 ms chunks of speech"""
    segment = st.Segment()
    for _ in range(chunks):
        segment.add(SPEECH)
    return segment


# --- streaming: committing ---


def test_words_of_and_common_prefix():
    """word lists come from segments; agreement ignores case and punctuation"""
    assert not st.words_of({"text": "x"})
    assert not st.words_of({"segments": [{"text": "x"}]})
    result = words_result(["Call", "use", "memo"])
    assert [word["word"] for word in st.words_of(result)] == [" Call", " use", " memo"]
    prev = st.words_of(words_result(["call,", "use", "mama"]))
    assert st.common_prefix(prev, st.words_of(result)) == 2
    assert st.common_prefix([], st.words_of(result)) == 0


def test_commit_agreed_words(monkeypatch):
    """words two results agree on are committed and their audio dropped"""
    monkeypatch.setattr(st.config, "COMMIT_MARGIN_MS", 100)
    segment = speech_segment(10)  # 500 ms
    segment.commit(words_result(["a", "b", "c", "d"]))
    assert segment.committed == "" and len(segment.window) == 10

    segment.commit(words_result(["a", "b", "c", "e", "f"]))
    assert segment.committed == " a b c"
    assert len(segment.window) == 7  # cut at "e", 150 ms in
    assert [word["word"] for word in segment.prev_words] == [" e", " f"]
    assert segment.context() == "a b c"


def test_commit_keeps_the_tail(monkeypatch):
    """words ending within the margin of the window's end stay uncommitted"""
    monkeypatch.setattr(st.config, "COMMIT_MARGIN_MS", 400)
    segment = speech_segment(10)
    segment.commit(words_result(["a", "b", "c", "d"]))
    segment.commit(words_result(["a", "b", "c", "d"]))
    # "a" and "b" end by 100 ms, outside the 400 ms margin
    assert segment.committed == " a b"
    assert len(segment.window) == 8


def test_commit_needs_an_uncommitted_word_and_a_whole_chunk(monkeypatch):
    """everything agreed, or a cut inside the first chunk, commits nothing"""
    monkeypatch.setattr(st.config, "COMMIT_MARGIN_MS", 0)
    segment = speech_segment(10)
    segment.commit(words_result(["a", "b"]))
    segment.commit(words_result(["a", "b"]))
    assert segment.committed == ""

    segment = speech_segment(10)
    segment.commit(words_result(["a", "b", "c"], step=0.01))
    segment.commit(words_result(["a", "b", "c"], step=0.01))
    assert segment.committed == "" and len(segment.window) == 10


def test_wants_words(monkeypatch):
    """word timestamps only for long windows, and only when committing is on"""
    monkeypatch.setattr(st.config, "COMMIT_AFTER_MS", 200)
    assert not speech_segment(3).wants_words()
    assert speech_segment(4).wants_words()
    monkeypatch.setattr(st.config, "COMMIT_PREFIX", False)
    assert not speech_segment(4).wants_words()


@pytest.mark.asyncio
async def test_transcribe_segment_options():
    """context and word timestamps are passed only when needed"""
    seen = []

    async def transcriber(_window, **options):
        seen.append(options)
        return {"text": ""}

    segment = speech_segment(2)
    await st.transcribe_segment(transcriber, segment)
    segment.committed = " use memo"
    await st.transcribe_segment(transcriber, segment, words=True)
    assert seen == [{}, {"context": "use memo", "words": True}]


@pytest.mark.asyncio
async def test_final_keeps_committed_text():
    """a final carries the committed text, even when the tail fails to transcribe"""
    results = []

    async def collect(result: dict) -> None:
        results.append(result)

    async def tail(_window, **_options):
        return {"text": " tail"}

    async def broken(_window, **_options):
        raise RuntimeError("boom")

    for transcriber, expected in [(tail, " head tail"), (broken, " head")]:
        segment = speech_segment(2)
        segment.committed = " head"
        await st.close_segment(transcriber, segment, collect)
        assert results[-1]["is_partial"] is False
        assert results[-1]["data"]["text"] == expected


@pytest.mark.asyncio
async def test_loop_commits_and_sends_full_text(monkeypatch):
    """partials show committed text plus the tail; the window shrinks"""
    monkeypatch.setattr(st.config, "COMMIT_AFTER_MS", 0)
    monkeypatch.setattr(st.config, "COMMIT_MARGIN_MS", 0)
    windows, contexts, results = [], [], []

    async def transcriber(window, context="", words=False):
        assert words
        windows.append(len(window))
        contexts.append(context)
        return numbered_words(window)

    async def collect(result: dict) -> None:
        results.append(result)

    queue, should_stop = Queue(), [False]
    task = asyncio.create_task(st.transcribe(should_stop, queue, transcriber, collect))
    for index in range(6):
        queue.put(numbered(index))
        await asyncio.sleep(0.03)
    should_stop[0] = True
    await task

    assert any(contexts)
    assert min(windows[1:]) < max(windows)
    # " w0" was committed from a 2-chunk window; the final still carries it
    sent = [(result["is_partial"], result["data"]["text"]) for result in results]
    assert (False, " w0 w1") in sent


# --- fast_server: context reaches the model ---


def test_ws_prompt_includes_committed_context(monkeypatch):
    """the session prompt and the committed text are combined"""
    monkeypatch.setattr(st.config, "COMMIT_AFTER_MS", 0)
    monkeypatch.setattr(st.config, "COMMIT_MARGIN_MS", 0)
    prompts = []

    async def fake(_model, chunks, _lang="en", prompt=None, word_timestamps=False):
        prompts.append((prompt, word_timestamps))
        # a last word that changes every call: results agree on a prefix, never fully
        names = [f"w{chunk[0]}" for chunk in chunks] + [f"x{len(prompts)}"]
        return words_result(names)

    monkeypatch.setattr(fs.ts, "transcribe_pcm_chunks_async", fake)
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text('{"type": "start", "prompt": "useMemo"}')
        for index in range(8):
            websocket.send_bytes(numbered(index))
        time.sleep(0.2)
        websocket.send_text('{"type": "stop"}')
        while websocket.receive_json()["is_partial"]:
            pass

    assert prompts[0] == ("useMemo", True)
    assert any(prompt.startswith("useMemo w0") for prompt, _ in prompts)


# --- transcriber: model pool ---


class SlowModel:  # pylint: disable=too-few-public-methods
    """records how many calls overlap"""

    def __init__(self) -> None:
        """ctor"""
        self.active = self.peak = 0
        self.lock = threading.Lock()
        self.kwargs = {}

    def __deepcopy__(self, _memo):
        """a fresh replica"""
        return SlowModel()

    def transcribe(self, _audio, **kwargs):
        """pretend to transcribe for 50 ms"""
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        with self.lock:
            self.active -= 1
        self.kwargs = kwargs
        return {"text": "ok"}


@pytest.mark.asyncio
async def test_pool_serializes_calls_on_one_replica():
    """one replica never runs two transcriptions at once"""
    model = SlowModel()
    pool = ts.ModelPool(model)
    await asyncio.gather(
        *[ts.transcribe_pcm_chunks_async(pool, [SPEECH]) for _ in range(4)]
    )
    assert model.peak == 1


@pytest.mark.asyncio
async def test_pool_replicas_run_in_parallel():
    """each replica is a separate copy that can run alongside the others"""
    pool = ts.ModelPool(SlowModel(), replicas=2)
    assert len(pool.replicas) == 2 and pool.replicas[0] is not pool.replicas[1]
    start = time.time()
    await asyncio.gather(
        *[
            ts.transcribe_pcm_chunks_async(pool, [SPEECH], word_timestamps=True)
            for _ in range(4)
        ]
    )
    assert time.time() - start < 0.18
    assert all(replica.peak == 1 for replica in pool.replicas)
    assert any(replica.kwargs.get("word_timestamps") for replica in pool.replicas)


def test_get_model_returns_a_cached_pool():
    """the server's model is a pool, loaded once"""
    pool = ts.get_model()
    assert isinstance(pool, ts.ModelPool)
    assert ts.get_model() is pool
