""" test scenario module """

import uuid
import asyncio
from queue import Queue
from typing import Callable


def get_all(queue: Queue) -> list:
    """get_all from queue"""
    res = []
    while queue and not queue.empty():
        res.append(queue.get())
    return res


async def transcribe(
    should_stop: list,
    queue: Queue,
    transcriber: Callable[[list], str],
    segment_closed: Callable[[dict], None],
):
    """the transcription loop"""
    window, prev_result, cycles = [], "", 0

    while not should_stop[0]:
        await asyncio.sleep(0.01)
        window.extend(get_all(queue))

        if not window:
            continue

        result = {"data": await transcriber(window), "is_partial": False}

        if should_close_segment(result, prev_result, cycles):
            window, prev_result, cycles = [], "", 0
            result["is_partial"] = True
        elif prev_result == result:
            cycles += 1
        else:
            cycles = 0
            prev_result = result

        await segment_closed(result)


def should_close_segment(result, prev_result, cycles, max_cycles=1):
    """return if segment should be closed"""
    return result == prev_result and cycles == max_cycles


class TrancribeSession:  # pylint: disable=too-few-public-methods
    """transcription state"""

    def __init__(self, transcribe_async, send_back_async) -> None:
        """ctor"""
        self.id = uuid.uuid4()  # pylint: disable=invalid-name
        self.queue = Queue()
        self.should_stop = [False]
        self.task = asyncio.create_task(
            transcribe(self.should_stop, self.queue, transcribe_async, send_back_async)
        )

    async def stop(self):
        """stop session"""
        self.should_stop[0] = True
        await self.task
