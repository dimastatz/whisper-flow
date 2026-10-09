""" streaming transcription module """

import re
import time
import uuid
import asyncio
import logging
from queue import Queue
from asyncio import FIRST_COMPLETED
from functools import partial
from typing import Callable, Optional

import numpy as np

from whisperflow import config


LOG = logging.getLogger(__name__)


def get_all(queue: Queue) -> list:
    """get_all from queue"""
    res = []
    while queue and not queue.empty():
        res.append(queue.get())
    return res


class FlushRequest:  # pylint: disable=too-few-public-methods
    """queue marker: finalize everything queued before it"""

    def __init__(self) -> None:
        """ctor"""
        self.done = asyncio.get_running_loop().create_future()


async def safe_transcribe(transcriber: Callable[[list], dict], window: list):
    """run the transcriber with a timeout, returning None on error/timeout"""
    try:
        return await asyncio.wait_for(
            transcriber(window), timeout=config.TRANSCRIBE_TIMEOUT
        )
    except asyncio.TimeoutError:
        LOG.warning("transcription timed out after %ss", config.TRANSCRIBE_TIMEOUT)
    except Exception:  # pylint: disable=broad-except
        LOG.exception("transcription failed")
    return None


def is_silent(chunk: bytes) -> bool:
    """true when every int16 sample in the chunk is below the silence threshold"""
    samples = np.frombuffer(chunk[: len(chunk) // 2 * 2], np.int16).astype(np.int32)
    return not samples.size or int(np.max(np.abs(samples))) < config.SILENCE_THRESHOLD


def duration_ms(chunk: bytes) -> float:
    """playback duration of an int16 mono chunk"""
    return len(chunk) / 2 / config.SAMPLE_RATE * 1000


def normalize(text: str) -> str:
    """lowercase and strip punctuation so cosmetic changes compare equal"""
    return " ".join(re.sub(r"[^\w\s]", "", text.lower()).split())


# characters of committed text passed back to Whisper as context
CONTEXT_CHARS = 200


def words_of(data: dict) -> list:
    """the word-level timestamps of a Whisper result, or [] when it has none"""
    return [
        word
        for segment in data.get("segments") or []
        for word in segment.get("words") or []
    ]


def common_prefix(prev: list, curr: list) -> int:
    """number of leading words two hypotheses agree on, ignoring case/punctuation"""
    count = 0
    for old, new in zip(prev, curr):
        if normalize(old["word"]) != normalize(new["word"]):
            break
        count += 1
    return count


class Segment:
    """audio of the segment being transcribed, plus its endpointing state

    With WF_COMMIT_PREFIX, words that two consecutive partials agree on are
    committed: their text moves to `committed` and their audio leaves the window.
    Each cycle then re-transcribes only the uncommitted tail instead of the whole
    segment, and the committed words no longer change between partials.
    """

    def __init__(self) -> None:
        """ctor"""
        self.window, self.prev_result, self.cycles = [], {}, 0
        self.has_speech, self.silent_ms = False, 0.0
        self.committed, self.prev_words = "", []

    def add(self, chunk: bytes):
        """append a chunk, tracking trailing silence"""
        self.window.append(chunk)
        if is_silent(chunk):
            self.silent_ms += duration_ms(chunk)
        else:
            self.has_speech, self.silent_ms = True, 0.0

        # before any speech, keep only WF_SILENCE_MS of lead-in audio
        while not self.has_speech and len(self.window) > 1:
            if self.silent_ms - duration_ms(self.window[0]) < config.SILENCE_MS:
                break
            self.silent_ms -= duration_ms(self.window.pop(0))

    def is_full(self) -> bool:
        """true when the window reached the cap"""
        return len(self.window) >= config.MAX_WINDOW_CHUNKS

    def ended_by_silence(self) -> bool:
        """true when speech was followed by WF_SILENCE_MS of silence"""
        return self.has_speech and self.silent_ms >= config.SILENCE_MS

    def wants_words(self) -> bool:
        """true when the window is long enough for committing to pay off"""
        window_ms = sum(duration_ms(chunk) for chunk in self.window)
        return config.COMMIT_PREFIX and window_ms >= config.COMMIT_AFTER_MS

    def context(self) -> str:
        """the end of the committed text, to keep Whisper's context across commits"""
        return self.committed[-CONTEXT_CHARS:].strip()

    def full_text(self, data: Optional[dict]) -> str:
        """committed text followed by the transcript of the uncommitted window"""
        return self.committed + ((data or {}).get("text") or "")

    def commit(self, data: dict) -> None:
        """commit the words this result agrees on with the previous one"""
        words = words_of(data)
        agreed = common_prefix(self.prev_words, words)
        window_ms = sum(duration_ms(chunk) for chunk in self.window)
        # keep the tail: words near the end of the window may still change
        while (
            agreed
            and words[agreed - 1]["end"] * 1000 > window_ms - config.COMMIT_MARGIN_MS
        ):
            agreed -= 1
        self.prev_words = words
        if not agreed or agreed >= len(words):
            return

        # cut where the first uncommitted word starts, on a chunk boundary
        cut_ms, dropped = words[agreed]["start"] * 1000, 0
        while (
            dropped < len(self.window) - 1
            and duration_ms(self.window[dropped]) <= cut_ms
        ):
            cut_ms -= duration_ms(self.window[dropped])
            dropped += 1
        if not dropped:
            return
        self.committed += "".join(word["word"] for word in words[:agreed])
        del self.window[:dropped]
        self.prev_words = words[agreed:]


async def transcribe_segment(
    transcriber: Callable[..., dict], segment: Segment, words: bool = False
):
    """transcribe the segment's window, passing committed text as context

    `words` asks for word timestamps, which committing needs. They make a call
    slower, so short windows, where re-transcribing is cheap, go without.
    """
    options = {}
    if segment.context():
        options["context"] = segment.context()
    if words:
        options["words"] = True
    return await safe_transcribe(partial(transcriber, **options), segment.window)


def with_committed(segment: Segment, data: Optional[dict]) -> dict:
    """the result data with the committed text in front of its transcript"""
    data = dict(data or {"text": ""})
    data["text"] = segment.full_text(data)
    return data


async def close_segment(
    transcriber: Callable[..., dict],
    segment: Segment,
    segment_closed: Callable[[dict], None],
) -> Segment:
    """send the segment's whole window as a final result; return a fresh one"""
    start = time.time()
    if segment.has_speech:
        data = await transcribe_segment(transcriber, segment)
        if data or segment.committed:
            data = with_committed(segment, data)
            if data["text"]:
                await segment_closed(
                    {
                        "is_partial": False,
                        "data": data,
                        "time": (time.time() - start) * 1000,
                    }
                )
    return Segment()


async def transcribe(
    should_stop: list,
    queue: Queue,
    transcriber: Callable[[list], dict],
    segment_closed: Callable[[dict], None],
):
    """the transcription loop"""
    segment = Segment()

    while not should_stop[0]:
        start = time.time()
        await asyncio.sleep(0.01)

        for item in get_all(queue):
            if isinstance(item, FlushRequest):
                segment = await close_segment(transcriber, segment, segment_closed)
                item.done.set_result(True)
                continue
            segment.add(item)
            if segment.is_full():
                # close the segment at the cap instead of dropping its start
                segment = await close_segment(transcriber, segment, segment_closed)

        if segment.ended_by_silence():
            segment = await close_segment(transcriber, segment, segment_closed)
            continue

        if not segment.has_speech:
            continue

        data = await transcribe_segment(transcriber, segment, segment.wants_words())
        if data is None:
            continue
        if config.COMMIT_PREFIX:
            # this result covers the whole window, so build it before committing
            full = with_committed(segment, data)
            segment.commit(data)
            data = full

        result = {
            "is_partial": True,
            "data": data,
            "time": (time.time() - start) * 1000,
        }

        if should_close_segment(result, segment.prev_result, segment.cycles):
            segment = Segment()
            result["is_partial"] = False
        elif same_text(result, segment.prev_result):
            segment.cycles += 1
        else:
            segment.cycles = 0
            segment.prev_result = result

        if result["data"]["text"]:
            await segment_closed(result)


def same_text(result: dict, prev_result: dict) -> bool:
    """true when two results differ only in case/punctuation/spacing"""
    return normalize(result["data"]["text"]) == normalize(
        prev_result.get("data", {}).get("text", "")
    )


def should_close_segment(result: dict, prev_result: dict, cycles, max_cycles=1):
    """return if segment should be closed"""
    return cycles >= max_cycles and same_text(result, prev_result)


class TranscribeSession:  # pylint: disable=too-few-public-methods
    """transcription state"""

    def __init__(self, transcribe_async, send_back_async) -> None:
        """ctor"""
        self.id = uuid.uuid4()  # pylint: disable=invalid-name
        self.queue = Queue()
        self.should_stop = [False]
        self.task = asyncio.create_task(
            transcribe(self.should_stop, self.queue, transcribe_async, send_back_async)
        )

    def add_chunk(self, chunk: bytes):
        """add new chunk"""
        self.queue.put_nowait(chunk)

    async def flush(self):
        """finalize all audio queued so far and send it as a final result"""
        request = FlushRequest()
        self.queue.put_nowait(request)
        await asyncio.wait({request.done, self.task}, return_when=FIRST_COMPLETED)

    async def stop(self):
        """stop session"""
        self.should_stop[0] = True
        await self.task
