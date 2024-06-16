""" test scenario module """

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
    segment_closed: Callable[[str], None],
):
    """the transcription loop"""
    window, prev_result, cycles = [], "", 0

    while not should_stop[0]:
        await asyncio.sleep(0.01)
        window.extend(get_all(queue))

        if not window:
            continue

        result = await transcriber(window)

        if should_close_segment(result, prev_result, cycles):
            window, prev_result, cycles = [], "", 0
            await segment_closed(result)
        elif prev_result == result:
            cycles += 1
        else:
            cycles = 0
            prev_result = result


def should_close_segment(result, prev_result, cycles, max_cycles=1):
    """return if segment should be closed"""
    return result == prev_result and cycles == max_cycles
