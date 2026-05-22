"""Demo task runner shim.

在本地演示环境里不强依赖 Celery/Redis，而是提供一个兼容 `.delay()` /
`.AsyncResult().revoke()` 接口的轻量包装，背后用独立 Python 子进程执行。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


_processes: dict[str, subprocess.Popen[str]] = {}
RUNNER_MODULE = "app.tasks.demo_task_runner"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass
class DemoAsyncResult:
    id: str

    def revoke(self, terminate: bool = False) -> None:
        process = _processes.get(self.id)
        if not process or process.poll() is not None:
            return None
        if terminate:
            process.terminate()
        return None


class DemoTask:
    def __init__(self, func: Callable[..., Any]):
        self.func = func

    def delay(self, *args: Any, **kwargs: Any) -> DemoAsyncResult:
        task_id = str(uuid.uuid4())
        runner_args = [
            sys.executable,
            "-m",
            RUNNER_MODULE,
            self.func.__module__,
            self.func.__name__,
            task_id,
            json.dumps(args),
            json.dumps(kwargs),
        ]
        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        support_paths = [
            str(_project_root()),
            str(_project_root() / "apps" / "api"),
            str(_project_root() / "skeleton"),
        ]
        env["PYTHONPATH"] = os.pathsep.join([*support_paths, python_path] if python_path else support_paths)
        process = subprocess.Popen(
            runner_args,
            cwd=str(_project_root()),
            env=env,
            start_new_session=True,
        )
        _processes[task_id] = process
        return DemoAsyncResult(id=task_id)

    def AsyncResult(self, task_id: str) -> DemoAsyncResult:  # noqa: N802
        return DemoAsyncResult(id=task_id)


class DemoCeleryApp:
    def task(self, bind: bool = False):  # noqa: ARG002
        def decorator(func: Callable[..., Any]) -> DemoTask:
            return DemoTask(func)

        return decorator


celery_app = DemoCeleryApp()
