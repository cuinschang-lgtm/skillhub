from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import normalize_database_url, settings
from app.models import Task


SYNC_DATABASE_URL = normalize_database_url(settings.database_url, async_mode=False)
sync_engine = create_engine(SYNC_DATABASE_URL, future=True)


def update_task(task_uuid: uuid.UUID, **fields) -> Task:
    with Session(sync_engine) as db:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        for key, value in fields.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        db.expunge(task)
        return task


def load_task(task_uuid: uuid.UUID) -> Task:
    with Session(sync_engine) as db:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        db.expunge(task)
        return task


def mark_task_failed_if_pending(task_id: str, error_message: str) -> bool:
    try:
        task_uuid = uuid.UUID(task_id)
    except (ValueError, TypeError):
        return False

    with Session(sync_engine) as db:
        task = db.get(Task, task_uuid)
        if not task or task.status != "pending":
            return False
        task.status = "failed"
        task.current_stage = "failed"
        task.error_message = error_message
        task.completed_at = datetime.utcnow()
        db.commit()
        return True
