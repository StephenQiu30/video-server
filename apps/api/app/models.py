from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from video_downloader_shared.states import TaskState


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    display_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_task_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    concurrent_task_quota: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=2147483648, nullable=False)
    file_retention_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, default=5368709120, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tasks: Mapped[list["DownloadTask"]] = relationship(back_populates="user")


class DownloadTask(Base):
    __tablename__ = "download_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    cover_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    format_id: Mapped[str | None] = mapped_column(String(100))
    format_label: Mapped[str | None] = mapped_column(String(255))
    retry_of_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("download_tasks.id", name="fk_download_tasks_retry_of_task_id"),
        index=True,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=TaskState.QUEUED.value, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    output_filename: Mapped[str | None] = mapped_column(String(255))
    object_key: Mapped[str | None] = mapped_column(Text)
    object_size: Mapped[int | None] = mapped_column(BigInteger)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    # AI Intelligence Suite
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_mindmap: Mapped[str | None] = mapped_column(Text)
    ai_status: Mapped[str | None] = mapped_column(String(32), index=True)
    ai_error: Mapped[str | None] = mapped_column(Text)
    # Enhanced Artifacts (subtitles, metadata)
    enhanced_status: Mapped[str | None] = mapped_column(String(32), index=True)
    subtitle_data: Mapped[str | None] = mapped_column(Text)
    video_metadata: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="tasks")
    events: Mapped[list["TaskEvent"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    @property
    def is_latest_attempt(self) -> bool:
        return getattr(self, "_is_latest_attempt", True)


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("download_tasks.id"), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[DownloadTask] = relationship(back_populates="events")
