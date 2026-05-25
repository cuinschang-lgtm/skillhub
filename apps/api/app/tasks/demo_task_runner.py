from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from app.tasks.task_state import mark_task_failed_if_pending


def _load_task_callable(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)
    return getattr(target, "func", target)


def _extract_task_id(args_json: str) -> Optional[str]:
    try:
        args = json.loads(args_json)
    except Exception:
        return None
    if not isinstance(args, list) or not args:
        return None
    task_id = args[0]
    return task_id if isinstance(task_id, str) else None


def _mark_startup(startup_marker: Optional[str]) -> None:
    if not startup_marker:
        return
    Path(startup_marker).write_text("started", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        raise SystemExit(
            "Usage: python -m app.tasks.demo_task_runner <module> <task_attr> <job_id> <args_json> <kwargs_json>"
        )

    module_name, attr_name, job_id, args_json, kwargs_json = argv[1:]
    task_id = _extract_task_id(args_json)
    startup_marker = os.environ.get("SKILLHUB_RUNNER_STARTUP_MARKER")

    try:
        task_callable = _load_task_callable(module_name, attr_name)
        args: list[Any] = json.loads(args_json)
        kwargs: dict[str, Any] = json.loads(kwargs_json)
        _mark_startup(startup_marker)
        task_callable(job_id, *args, **kwargs)
        return 0
    except Exception as exc:
        error_message = f"Task runner startup failed: {type(exc).__name__}: {exc}"
        if task_id:
            mark_task_failed_if_pending(task_id, error_message)
        print(error_message, file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
