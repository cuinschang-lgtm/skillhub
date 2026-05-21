import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(20), nullable=False)
    display_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    skills = relationship("Skill", back_populates="user")
    tasks = relationship("Task", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    book_title = Column(String(500), nullable=False)
    domain = Column(String(200))
    skill_name = Column(String(64), nullable=False)
    skill_slug = Column(String(64), nullable=False, default="textbook-skill")
    visibility = Column(String(20), default="private")
    llm_provider = Column(String(30), default="deepseek")
    ocr_provider = Column(String(30), default="mineru")
    pdf_path = Column(Text, nullable=False)
    work_dir = Column(Text)
    current_stage = Column(String(20))
    progress_pct = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    celery_task_id = Column(String(255))

    user = relationship("User", back_populates="tasks")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(64), nullable=False)
    book_title = Column(String(500), nullable=False)
    domain = Column(String(200))
    visibility = Column(String(20), default="private")
    skill_dir = Column(Text, nullable=False)
    chapter_count = Column(Integer)
    benchmark_verdict = Column(String(100))
    benchmark_delta = Column(Float)
    benchmark_p_value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="skills")


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False)
    total_questions = Column(Integer)
    with_correct = Column(Integer)
    without_correct = Column(Integer)
    delta_pct = Column(Float)
    p_value = Column(Float)
    ci_lower = Column(Float)
    ci_upper = Column(Float)
    verdict = Column(String(200))
    per_chapter_json = Column(JSON)
    per_difficulty_json = Column(JSON)
    routing_accuracy = Column(Float)
    raw_results_path = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(200))
    active_skill_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
