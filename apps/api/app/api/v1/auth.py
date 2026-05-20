from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str
    role: str = "student"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/send-code")
async def send_code(req: SendCodeRequest):
    # TODO: Generate code, store in DB, send email
    return {"message": "验证码已发送", "email": req.email}


@router.post("/verify", response_model=TokenResponse)
async def verify(req: VerifyRequest):
    # TODO: Verify code, create/find user, issue JWT
    return TokenResponse(
        access_token="mock-jwt-token",
        user={"email": req.email, "role": req.role, "display_name": req.email.split("@")[0]},
    )


@router.get("/me")
async def get_me():
    # TODO: Decode JWT from header, return user
    return {"id": "mock-id", "email": "zhang@university.edu.cn", "role": "teacher", "display_name": "张老师"}
