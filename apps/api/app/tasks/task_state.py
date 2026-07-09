from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import (
    normalize_database_url,
    settings,
    should_use_storage_sqlite_fallback,
    storage_sqlite_database_url,
)
from app.models import Task


T = TypeVar("T")
_sync_database_url = normalize_database_url(settings.database_url, async_mode=False)
_sync_engine = create_engine(_sync_database_url, future=True)


def _create_sync_engine(database_url: str) -> Engine:
    return create_engine(normalize_database_url(database_url, async_mode=False), future=True)


def _use_sync_database_url(database_url: str) -> str:
    global _sync_database_url, _sync_engine

    normalized_url = normalize_database_url(database_url, async_mode=False)
    old_engine = _sync_engine
    _sync_database_url = normalized_url
    settings.database_url = normalize_database_url(database_url, async_mode=True)
    os.environ["DATABASE_URL"] = settings.database_url
    _sync_engine = _create_sync_engine(normalized_url)
    old_engine.dispose()
    return normalized_url


def _run_with_retry(operation: Callable[[Session], T]) -> T:
    try:
        with Session(_sync_engine) as db:
            return operation(db)
    except Exception as exc:
        fallback_url = storage_sqlite_database_url(async_mode=False)
        if _sync_database_url == fallback_url or not should_use_storage_sqlite_fallback(_sync_database_url, exc):
            raise
        _use_sync_database_url(fallback_url)
        with Session(_sync_engine) as db:
            return operation(db)


def run_in_sync_session(operation: Callable[[Session], T]) -> T:
    return _run_with_retry(operation)


def update_task(task_uuid: uuid.UUID, **fields) -> Task:
    def operation(db: Session) -> Task:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        for key, value in fields.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        db.expunge(task)
        return task

    return _run_with_retry(operation)


def load_task(task_uuid: uuid.UUID) -> Task:
    def operation(db: Session) -> Task:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        db.expunge(task)
        return task

    return _run_with_retry(operation)


def mark_task_failed_if_pending(task_id: str, error_message: str) -> bool:
    try:
        task_uuid = uuid.UUID(task_id)
    except (ValueError, TypeError):
        return False

    def operation(db: Session) -> bool:
        task = db.get(Task, task_uuid)
        if not task or task.status != "pending":
            return False
        task.status = "failed"
        task.current_stage = "failed"
        task.error_message = error_message
        task.completed_at = datetime.utcnow()
        db.commit()
        return True

    return _run_with_retry(operation)
