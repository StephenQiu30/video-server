from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token, hash_password
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)
LOCAL_USER_EMAIL = "local@stephen.video"


def get_or_create_local_user(db: Session) -> User:
    user = db.query(User).filter(User.email == LOCAL_USER_EMAIL).one_or_none()
    if user:
        return user

    settings = get_settings()
    user = User(
        email=LOCAL_USER_EMAIL,
        password_hash=hash_password("local-only"),
        display_name="本地用户",
        is_admin=False,
        daily_task_quota=settings.default_daily_task_quota,
        concurrent_task_quota=settings.per_user_download_concurrency,
        max_file_size_bytes=settings.max_file_size_bytes,
        file_retention_hours=settings.file_retention_hours,
        storage_quota_bytes=settings.default_storage_quota_bytes,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        return get_or_create_local_user(db)
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise AppError("unauthorized", "用户不存在或已停用", status_code=401)
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise AppError("forbidden", "需要管理员权限", status_code=403)
    return current_user
