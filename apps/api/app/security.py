from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from jose import JWTError, jwt

from app.config import settings


ALGORITHM = "HS256"


@dataclass
class TokenPayload:
    user_id: UUID
    email: str


def create_access_token(*, user_id: UUID, email: str, expires_minutes: int) -> tuple[str, int]:
    expires_in_seconds = max(expires_minutes, 1) * 60
    expire_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_in_seconds


def decode_access_token(token: str) -> TokenPayload:
    unauthorized = HTTPException(status_code=401, detail="Invalid or expired access token")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise unauthorized
        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id or not email:
            raise unauthorized
        return TokenPayload(user_id=UUID(user_id), email=str(email))
    except (JWTError, ValueError, TypeError) as exc:
        raise unauthorized from exc


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return token.strip()
