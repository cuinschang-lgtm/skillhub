from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user
from app.db import get_db
from app.models import Skill, Task, User


def _resolve_support_dir(name: str) -> Path:
    file_path = Path(__file__).resolve()
    candidates = [parent / name for parent in file_path.parents]
    candidates.append(Path.cwd() / name)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in seen)
    raise RuntimeError(f"Unable to locate {name} directory. Checked: {searched}")


SKELETON_DIR = _resolve_support_dir("skeleton")
PROMPTS_DIR = _resolve_support_dir("prompts")
if str(SKELETON_DIR) not in sys.path:
    sys.path.insert(0, str(SKELETON_DIR))

from bench import _parse_chapter_topics, load_skill, route_chapter_topk  # noqa: E402
from llm import LLMClient, LLMError  # noqa: E402


router = APIRouter()

ROUTING_PROMPT = (PROMPTS_DIR / "routing.md").read_text(encoding="utf-8")
MAX_REFERENCE_CHARS = 4000
MAX_EXCERPT_CHARS = 220


class ChatRequest(BaseModel):
    question: str
    active_skill_ids: list[str]


class ChatCitation(BaseModel):
    skill_id: str
    skill_name: str
    chapter: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]


def _chapter_excerpt(content: str) -> str:
    cleaned = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(cleaned) <= MAX_EXCERPT_CHARS:
        return cleaned
    return f"{cleaned[:MAX_EXCERPT_CHARS].rstrip()}..."


async def _load_visible_skill(skill_id: str, db: AsyncSession, user: User) -> Skill:
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid skill id: {skill_id}") from exc

    skill = await db.get(Skill, skill_uuid)
    if not skill or (skill.visibility != "public" and skill.user_id != user.id):
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


async def _resolve_provider(skills: list[Skill], db: AsyncSession) -> str:
    for skill in skills:
        if not skill.task_id:
            continue
        task = await db.get(Task, skill.task_id)
        if task and task.llm_provider:
            return task.llm_provider
    return settings.default_llm_provider


@router.post("", response_model=ChatResponse)
async def ask_question(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    if not payload.active_skill_ids:
        raise HTTPException(status_code=400, detail="Please activate at least one skill")

    deduped_skill_ids = list(dict.fromkeys(payload.active_skill_ids))[:4]
    skills = [await _load_visible_skill(skill_id, db, user) for skill_id in deduped_skill_ids]
    provider = await _resolve_provider(skills, db)

    references: list[str] = []
    citations: list[ChatCitation] = []

    try:
        client = LLMClient.from_env(provider)

        for skill in skills:
            skill_dir = Path(skill.skill_dir)
            if not skill_dir.exists():
                continue

            skill_md, chapters = load_skill(skill_dir)
            chapter_topics = _parse_chapter_topics(skill_md, list(chapters.keys()))
            selected = route_chapter_topk(
                client=client,
                prompt_template=ROUTING_PROMPT,
                question={"question": question, "topic": skill.domain or skill.book_title},
                chapter_topics=chapter_topics,
                k=1,
            )

            if not selected:
                continue

            chapter_name = selected[0]
            chapter_content = chapters.get(chapter_name, "").strip()
            if not chapter_content:
                continue

            references.append(
                f"[教材: {skill.book_title} | 章节: {chapter_name}]\n"
                f"{chapter_content[:MAX_REFERENCE_CHARS]}"
            )
            citations.append(
                ChatCitation(
                    skill_id=str(skill.id),
                    skill_name=skill.book_title,
                    chapter=chapter_name,
                    excerpt=_chapter_excerpt(chapter_content),
                )
            )

        if not references:
            raise HTTPException(status_code=410, detail="所选 Skill 文件已失效，请返回知识库或重新编译教材后再试")

        reference_block = "\n\n---\n\n".join(references) if references else "(未命中教材章节，请谨慎回答)"
        system = (
            "你是 SkillHub 教材问答助手。优先依据给定教材参考回答，表达清晰、公式完整、尽量贴合教材术语。"
            "如果参考不足，请先明确说明“教材中未直接覆盖”，再给出基于通用知识的谨慎回答。\n\n"
            "参考片段如下：\n====\n"
            f"{reference_block}\n"
            "===="
        )
        answer = client.chat([{"role": "user", "content": question}], system=system)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(answer=answer, citations=citations)
