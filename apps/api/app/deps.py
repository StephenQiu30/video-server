from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.models import User

LOCAL_USER_EMAIL = "local@stephen.video"


def get_or_create_local_user(db: Session) -> User:
    settings = get_settings()
    user = db.query(User).filter(User.email == LOCAL_USER_EMAIL).one_or_none()
    if user:
        user.display_name = "本地用户"
        user.is_active = True
        user.is_admin = False
        user.daily_task_quota = -1
        user.concurrent_task_quota = settings.per_user_download_concurrency
        user.max_file_size_bytes = settings.max_file_size_bytes
        user.file_retention_hours = settings.file_retention_hours
        user.storage_quota_bytes = -1
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=LOCAL_USER_EMAIL,
        password_hash=hash_password("local-only"),
        display_name="本地用户",
        is_admin=False,
        daily_task_quota=-1,
        concurrent_task_quota=settings.per_user_download_concurrency,
        max_file_size_bytes=settings.max_file_size_bytes,
        file_retention_hours=settings.file_retention_hours,
        storage_quota_bytes=-1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return get_or_create_local_user(db)
