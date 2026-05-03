from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None = None
    is_active: bool
    is_admin: bool
    daily_task_quota: int
    concurrent_task_quota: int
    max_file_size_bytes: int
    file_retention_hours: int
    storage_quota_bytes: int
    created_at: datetime


class ParseRequest(BaseModel):
    url: HttpUrl


class VideoFormat(BaseModel):
    format_id: str
    label: str
    ext: str | None = None
    resolution: str | None = None
    filesize: int | None = None


class ParseResponse(BaseModel):
    url: str
    title: str | None = None
    cover_url: str | None = None
    duration_seconds: int | None = None
    formats: list[VideoFormat]


class TaskCreate(BaseModel):
    url: HttpUrl
    format_id: str | None = None
    title: str | None = Field(default=None, max_length=500)
    cover_url: str | None = None
    duration_seconds: int | None = None
    format_label: str | None = Field(default=None, max_length=255)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_url: str
    title: str | None = None
    cover_url: str | None = None
    duration_seconds: int | None = None
    format_id: str | None = None
    format_label: str | None = None
    state: str
    progress: int
    failure_code: str | None = None
    failure_reason: str | None = None
    output_filename: str | None = None
    object_size: int | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DownloadLinkResponse(BaseModel):
    url: str
    expires_in_seconds: int


class HealthResponse(BaseModel):
    status: str
    app: str
