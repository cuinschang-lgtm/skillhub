from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class TaskResponse(BaseModel):
    id: str
    status: str
    book_title: str
    skill_name: str
    current_stage: Optional[str]
    progress_pct: int


@router.post("")
async def create_task(
    pdf: UploadFile = File(...),
    book_title: str = Form(...),
    domain: str = Form(""),
    skill_name: str = Form(...),
    visibility: str = Form("private"),
    llm_provider: str = Form("deepseek"),
    ocr_provider: str = Form("mineru"),
):
    # TODO: Save PDF, create task record, dispatch Celery task
    return {
        "id": "mock-task-id",
        "status": "pending",
        "book_title": book_title,
        "skill_name": skill_name,
        "current_stage": None,
        "progress_pct": 0,
    }


@router.get("")
async def list_tasks():
    # TODO: Query user's tasks
    return {"items": [], "total": 0}


@router.get("/{task_id}")
async def get_task(task_id: str):
    # TODO: Fetch task status
    return {"id": task_id, "status": "running", "current_stage": "ocr", "progress_pct": 45}


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    # TODO: Cancel Celery task
    return {"message": "cancelled"}
