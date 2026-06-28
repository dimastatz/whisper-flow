""" streaming transcription module """

import time
import uuid
import asyncio
import logging
from queue import Queue
from typing import Callable

from whisperflow import config


LOG = logging.getLogger(__name__)


def get_all(queue: Queue) -> list:
    """get_all from queue"""
    res = []
    while queue and not queue.empty():
        res.append(queue.get())
    return res


def trim_window(window: list, max_size: int) -> list:
    """keep the window bounded to the most recent max_size chunks"""
    if len(window) > max_size:
        return window[-max_size:]
    return window


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


async def transcribe(
    should_stop: list,
    queue: Queue,
    transcriber: Callable[[list], dict],
    segment_closed: Callable[[dict], None],
):
    """the transcription loop"""
    window, prev_result, cycles = [], {}, 0

    while not should_stop[0]:
        start = time.time()
        await asyncio.sleep(0.01)
        window.extend(get_all(queue))
        window = trim_window(window, config.MAX_WINDOW_CHUNKS)

        if not window:
            continue

        data = await safe_transcribe(transcriber, window)
        if data is None:
            continue

        result = {
            "is_partial": True,
            "data": data,
            "time": (time.time() - start) * 1000,
        }

        if should_close_segment(result, prev_result, cycles):
            window, prev_result, cycles = [], {}, 0
            result["is_partial"] = False
        elif result["data"]["text"] == prev_result.get("data", {}).get("text", ""):
            cycles += 1
        else:
            cycles = 0
            prev_result = result

        if result["data"]["text"]:
            await segment_closed(result)


def should_close_segment(result: dict, prev_result: dict, cycles, max_cycles=1):
    """return if segment should be closed"""
    return cycles >= max_cycles and result["data"]["text"] == prev_result.get(
        "data", {}
    ).get("text", "")


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

    async def stop(self):
        """stop session"""
        self.should_stop[0] = True
        await self.task
