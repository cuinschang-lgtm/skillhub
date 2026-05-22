from __future__ import annotations

import importlib
import json
import sys
from typing import Any


def _load_task_callable(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)
    return getattr(target, "func", target)


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        raise SystemExit(
            "Usage: python -m app.tasks.demo_task_runner <module> <task_attr> <job_id> <args_json> <kwargs_json>"
        )

    module_name, attr_name, job_id, args_json, kwargs_json = argv[1:]
    task_callable = _load_task_callable(module_name, attr_name)
    args: list[Any] = json.loads(args_json)
    kwargs: dict[str, Any] = json.loads(kwargs_json)
    task_callable(job_id, *args, **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
