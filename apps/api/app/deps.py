from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AppError("unauthorized", "请先登录后再操作", status_code=401)
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise AppError("unauthorized", "用户不存在或已停用", status_code=401)
    return user

