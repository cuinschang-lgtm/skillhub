from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.security import create_access_token

router = APIRouter()


class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str
    role: str = "student"
    remember: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


FIXED_CODE = "123456"


def serialize_user(user: User) -> dict[str, str]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name or user.email.split("@")[0],
    }


@router.post("/send-code")
async def send_code(req: SendCodeRequest):
    return {"message": f"演示环境不发邮件，验证码固定为 {FIXED_CODE}", "email": req.email}


@router.post("/verify", response_model=TokenResponse)
async def verify(req: VerifyRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.strip().lower()
    code = req.code.strip()
    role = "teacher" if req.role.strip().lower() == "teacher" else "student"
    display_name = email.split("@")[0] or email

    if code != FIXED_CODE:
        raise HTTPException(status_code=401, detail="验证码错误")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.role = role
        user.display_name = display_name
        user.last_login_at = datetime.utcnow()
    else:
        user = User(
            email=email,
            role=role,
            display_name=display_name,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise
        user.role = role
        user.display_name = display_name
        user.last_login_at = datetime.utcnow()
        await db.commit()

    await db.refresh(user)
    expires_minutes = settings.jwt_expire_minutes if req.remember else 60 * 24
    access_token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        expires_minutes=expires_minutes,
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=serialize_user(user),
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return serialize_user(user)
