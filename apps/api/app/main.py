from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db import init_db
from app.ws.progress import router as ws_router

app = FastAPI(
    title="SkillHub API",
    description="教材知识 Skill 编译与问答平台",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
