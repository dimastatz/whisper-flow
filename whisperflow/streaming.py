""" streaming transcription module """

import time
import uuid
import asyncio
import logging
from queue import Queue
from asyncio import FIRST_COMPLETED
from typing import Callable

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


async def close_segment(
    transcriber: Callable[[list], dict],
    window: list,
    segment_closed: Callable[[dict], None],
):
    """transcribe the whole window and send it as a final result"""
    start = time.time()
    data = await safe_transcribe(transcriber, window) if window else None
    if data and data["text"]:
        await segment_closed(
            {"is_partial": False, "data": data, "time": (time.time() - start) * 1000}
        )


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

        for item in get_all(queue):
            if isinstance(item, FlushRequest):
                await close_segment(transcriber, window, segment_closed)
                window, prev_result, cycles = [], {}, 0
                item.done.set_result(True)
                continue
            window.append(item)
            if len(window) >= config.MAX_WINDOW_CHUNKS:
                # close the segment at the cap instead of dropping its start
                await close_segment(transcriber, window, segment_closed)
                window, prev_result, cycles = [], {}, 0

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

    async def flush(self):
        """finalize all audio queued so far and send it as a final result"""
        request = FlushRequest()
        self.queue.put_nowait(request)
        await asyncio.wait({request.done, self.task}, return_when=FIRST_COMPLETED)

    async def stop(self):
        """stop session"""
        self.should_stop[0] = True
        await self.task
