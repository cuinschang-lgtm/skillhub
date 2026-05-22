from fastapi import APIRouter

from app.api.v1 import auth, chat, skills, tasks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
