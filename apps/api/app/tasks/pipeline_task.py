"""Pipeline Celery task — wraps skeleton/pipeline.py with progress reporting."""

import json
import redis
from pathlib import Path

from app.tasks.celery_app import celery_app
from app.config import settings


def publish_progress(task_id: str, stage: str, status: str, message: str = "", progress: int = 0, extra: dict = None):
    r = redis.from_url(settings.redis_url)
    payload = {
        "stage": stage,
        "status": status,
        "message": message,
        "progress": progress,
        "extra": extra or {},
    }
    r.publish(f"task:{task_id}:progress", json.dumps(payload, ensure_ascii=False))


@celery_app.task(bind=True)
def run_pipeline_task(self, task_id: str, config: dict):
    """Run the textbook2skill pipeline as a background task.

    config keys: pdf_path, skill_name, book_title, domain, work_dir,
                 ocr_provider, llm_provider, user_api_keys
    """
    # TODO: Full implementation that:
    # 1. Sets up environment variables from user_api_keys
    # 2. Calls modified pipeline.py with progress_callback
    # 3. On completion: creates Skill record in DB
    # 4. On failure: updates task status with error

    publish_progress(task_id, "probe", "running", "正在探测 PDF...")

    # Placeholder — actual implementation will import and call skeleton code
    publish_progress(task_id, "probe", "done", "PDF 探测完成", progress=100)
    publish_progress(task_id, "ocr", "running", "正在进行 OCR...")

    return {"status": "completed", "task_id": task_id}
