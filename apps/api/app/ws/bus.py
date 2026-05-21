from __future__ import annotations

import asyncio
from collections import defaultdict


class ProgressBus:
    def __init__(self) -> None:
        self._channels: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)

    def subscribe(self, task_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._channels[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[str]) -> None:
        subscribers = self._channels.get(task_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._channels.pop(task_id, None)

    def publish(self, task_id: str, payload: str) -> None:
        for queue in list(self._channels.get(task_id, ())):
            queue.put_nowait(payload)


progress_bus = ProgressBus()
