from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user
from app.db import get_db
from app.models import Skill, Task, User
from app.tasks.pipeline_task import run_pipeline_task
from app.utils import slugify_skill_name

router = APIRouter()


class TaskResponse(BaseModel):
    id: str
    status: str
    book_title: str
    skill_name: str
    skill_slug: str
    current_stage: Optional[str]
    progress_pct: int


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


def _to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        status=task.status,
        book_title=task.book_title,
        skill_name=task.skill_name,
        skill_slug=task.skill_slug or task.skill_name,
        current_stage=task.current_stage,
        progress_pct=task.progress_pct or 0,
    )


@router.post("")
async def create_task(
    pdf: UploadFile = File(...),
    book_title: str = Form(...),
    domain: str = Form(""),
    skill_name: str = Form(...),
    visibility: str = Form("private"),
    llm_provider: str = Form(settings.default_llm_provider),
    ocr_provider: str = Form("mineru"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    task_id = uuid.uuid4()
    base_dir = Path(settings.storage_dir).resolve()
    work_dir = base_dir / "tasks" / str(task_id)
    input_dir = work_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = input_dir / "input.pdf"
    pdf_path.write_bytes(await pdf.read())

    skill_name = skill_name.strip() or book_title.strip()
    skill_slug = slugify_skill_name(skill_name, fallback="textbook-skill")

    task = Task(
        id=task_id,
        user_id=user.id,
        status="pending",
        book_title=book_title,
        domain=domain,
        skill_name=skill_name,
        skill_slug=skill_slug,
        visibility="public" if visibility == "public" else "private",
        llm_provider=llm_provider,
        ocr_provider=ocr_provider,
        pdf_path=str(pdf_path),
        work_dir=str(work_dir),
        current_stage="queued",
        progress_pct=0,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = run_pipeline_task.delay(str(task.id))
    task.celery_task_id = celery_result.id
    await db.commit()
    await db.refresh(task)

    return _to_response(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task)
        .where(Task.user_id == user.id)
        .order_by(desc(Task.created_at))
    )
    tasks = list(result.scalars().all())
    return TaskListResponse(items=[_to_response(task) for task in tasks], total=len(tasks))


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = await db.get(Task, uuid.UUID(task_id))
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    skill_id: Optional[str] = None
    skill_result = await db.execute(select(Skill).where(Skill.task_id == task.id))
    skill = skill_result.scalar_one_or_none()
    if skill:
        skill_id = str(skill.id)

    return {
        **_to_response(task).model_dump(),
        "domain": task.domain,
        "visibility": task.visibility,
        "skill_slug": task.skill_slug,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "skill_id": skill_id,
    }


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = await db.get(Task, uuid.UUID(task_id))
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.celery_task_id:
        run_pipeline_task.AsyncResult(task.celery_task_id).revoke(terminate=True)
    task.status = "cancelled"
    task.current_stage = "cancelled"
    task.completed_at = datetime.utcnow()
    await db.commit()
    return {"message": "cancelled"}
