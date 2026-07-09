import importlib
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.db import get_engine, init_db
from app.maintenance import cleanup_stale_skills, ensure_prebuilt_demo_skill, ensure_storage_ready
from app.ws.progress import router as ws_router

app = FastAPI(
    title="SkillHub API",
    description="教材知识 Skill 编译与问答平台",
    version="0.1.0",
)

cors_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.on_event("startup")
async def startup() -> None:
    ensure_storage_ready(settings.storage_dir)
    await init_db()
    await cleanup_stale_skills()
    await ensure_prebuilt_demo_skill()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/deep")
async def deep_health():
    checks: dict[str, str] = {}
    status_code = 200
    overall_status = "ok"

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        overall_status = "error"
        status_code = 503

    storage_dir = Path(settings.storage_dir)
    if storage_dir.is_dir() and os.access(storage_dir, os.R_OK | os.W_OK):
        checks["storage"] = "ok"
    else:
        checks["storage"] = "error"
        overall_status = "error"
        status_code = 503

    try:
        if not os.access(sys.executable, os.X_OK):
            checks["task_runner"] = "error"
            overall_status = "error"
            status_code = 503
        else:
            importlib.import_module("app.tasks.demo_task_runner")
            checks["task_runner"] = "ok"
    except Exception:
        checks["task_runner"] = "error"
        overall_status = "error"
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "checks": checks,
        },
    )
