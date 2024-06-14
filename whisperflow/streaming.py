""" test scenario module """

import asyncio
from queue import Queue


def get_all(queue: Queue) -> list:
    """get_all from queue"""
    res = []
    while queue and not queue.empty():
        res.append(queue.get())
    return res


async def transcribe(should_stop: list, queue: Queue):
    """the transcription loop"""
    while not should_stop[0]:
        await asyncio.sleep(0.01)
        items = get_all(queue)

        if not items:
            continue
