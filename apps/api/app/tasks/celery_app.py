"""Demo task runner shim.

在本地演示环境里不强依赖 Celery/Redis，而是提供一个兼容 `.delay()` /
`.AsyncResult().revoke()` 接口的轻量包装，背后用 daemon thread 执行。
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable


_threads: dict[str, threading.Thread] = {}


@dataclass
class DemoAsyncResult:
    id: str

    def revoke(self, terminate: bool = False) -> None:  # noqa: ARG002
        # 线程不可安全强杀；取消由任务自己检查 DB 状态决定。
        return None


class DemoTask:
    def __init__(self, func: Callable[..., Any]):
        self.func = func

    def delay(self, *args: Any, **kwargs: Any) -> DemoAsyncResult:
        task_id = str(uuid.uuid4())

        def runner() -> None:
            self.func(task_id, *args, **kwargs)

        thread = threading.Thread(target=runner, daemon=True)
        _threads[task_id] = thread
        thread.start()
        return DemoAsyncResult(id=task_id)

    def AsyncResult(self, task_id: str) -> DemoAsyncResult:  # noqa: N802
        return DemoAsyncResult(id=task_id)


class DemoCeleryApp:
    def task(self, bind: bool = False):  # noqa: ARG002
        def decorator(func: Callable[..., Any]) -> DemoTask:
            return DemoTask(func)

        return decorator


celery_app = DemoCeleryApp()
