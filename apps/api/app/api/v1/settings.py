from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import User

router = APIRouter()


class ProfileResponse(BaseModel):
    email: str
    role: str
    display_name: str


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(default="", max_length=100)


def _serialize_profile(user: User) -> ProfileResponse:
    return ProfileResponse(
        email=user.email,
        role=user.role,
        display_name=user.display_name or user.email.split("@")[0] or user.email,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return _serialize_profile(user)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    display_name = payload.display_name.strip()
    user.display_name = display_name or None
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _serialize_profile(user)
