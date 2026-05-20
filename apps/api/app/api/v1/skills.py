from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SkillResponse(BaseModel):
    id: str
    name: str
    book_title: str
    domain: Optional[str]
    visibility: str
    chapter_count: Optional[int]
    benchmark_verdict: Optional[str]
    benchmark_delta: Optional[float]


@router.get("")
async def list_skills(search: str = "", domain: str = "", page: int = 1, page_size: int = 20):
    # TODO: Query DB with filters
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    # TODO: Fetch from DB
    return {"id": skill_id, "name": "mock-skill", "book_title": "Mock Book"}


@router.get("/{skill_id}/chapters/{filename}")
async def get_chapter(skill_id: str, filename: str):
    # TODO: Read chapter file from storage
    return {"filename": filename, "content": "# Mock chapter content"}


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    # TODO: Delete from DB + storage
    return {"message": "deleted"}
