from __future__ import annotations

from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=100)
    role: str = Field(default="student")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


FIXED_CODE = "123456"

# bcrypt 单条密码长度上限 72 字节
MAX_PASSWORD_BYTES = 72


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], password_hash.encode("utf-8"))
    except ValueError:
        return False


async def _issue_token(user: User, remember: bool = False) -> TokenResponse:
    expires_minutes = settings.jwt_expire_minutes if remember else 60 * 24
    access_token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        expires_minutes=expires_minutes,
    )
    return TokenResponse(access_token=access_token, expires_in=expires_in, user=serialize_user(user))


def serialize_user(user: User) -> dict[str, str]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name or user.email.split("@")[0],
    }


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.strip().lower()
    if req.role not in ("teacher", "student"):
        raise HTTPException(status_code=400, detail="角色不合法")

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    user = User(
        email=email,
        role=req.role,
        display_name=(req.display_name.strip() or email.split("@")[0])[:100],
        password_hash=_hash_password(req.password),
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")
    await db.refresh(user)
    return await _issue_token(user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return await _issue_token(user)


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
    return await _issue_token(user, remember=req.remember)


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return serialize_user(user)
