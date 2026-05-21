from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User


@dataclass
class DemoUser:
    id: str
    email: str
    role: str
    display_name: str


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    x_demo_email: str | None = Header(default=None),
    x_demo_role: str | None = Header(default=None),
    x_demo_name: str | None = Header(default=None),
) -> User:
    email = (x_demo_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Missing demo user context")

    role = "teacher" if (x_demo_role or "").strip().lower() == "teacher" else "student"
    display_name = (x_demo_name or email.split("@")[0] or "Demo User").strip()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if user.role != role or user.display_name != display_name:
            user.role = role
            user.display_name = display_name
            await db.commit()
            await db.refresh(user)
        return user

    user = User(email=email, role=role, display_name=display_name)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        # 并发首访时，多个请求可能同时尝试创建同一 demo 用户。
        await db.rollback()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise
        if user.role != role or user.display_name != display_name:
            user.role = role
            user.display_name = display_name
            await db.commit()
            await db.refresh(user)
        return user
