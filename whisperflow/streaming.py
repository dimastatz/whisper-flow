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
    window, prev_result = [], ""

    while not should_stop[0]:
        await asyncio.sleep(0.01)
        window.extend(get_all(queue))

        if not window:
            continue

        result = await transcriber(window)

        if result == prev_result:
            window, prev_result = [], ""
        else:
            prev_result = result
            await segment_closed(result)
