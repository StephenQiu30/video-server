from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.deps import require_admin
from app.models import DownloadTask, User
from app.schemas import AdminUserUpdate, TaskRead, UserRead

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[User]:
    return list(db.scalars(select(User).order_by(desc(User.created_at)).limit(100)))


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise AppError("not_found", "用户不存在", 404)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/tasks", response_model=list[TaskRead])
def list_all_tasks(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DownloadTask]:
    return list(db.scalars(select(DownloadTask).order_by(desc(DownloadTask.created_at)).limit(100)))
