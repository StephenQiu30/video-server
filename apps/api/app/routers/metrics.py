from typing import Annotated

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.deps import get_current_active_admin
from app.models import DownloadTask, User
from app.schemas import AdminMetricsResponse
from video_downloader_shared.states import ACTIVE_TASK_STATES

router = APIRouter(prefix="/api/admin/metrics", tags=["admin", "metrics"])


@router.get("", response_model=AdminMetricsResponse)
def get_metrics(
    _: Annotated[User, Depends(get_current_active_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    settings = get_settings()
    
    # Active tasks
    active_values = [state.value for state in ACTIVE_TASK_STATES]
    active_tasks_count = db.scalar(
        select(func.count()).select_from(DownloadTask).where(DownloadTask.state.in_(active_values))
    )
    
    # Total users
    total_users = db.scalar(select(func.count()).select_from(User))
    
    # Storage usage
    total_storage_bytes = db.scalar(select(func.sum(DownloadTask.object_size))) or 0
    
    # Queue depth (if Redis is available)
    queue_depth = 0
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        queue_depth = redis.llen(f"rq:queue:{settings.rq_queue_name}")
    except Exception:
        pass

    return {
        "active_tasks": active_tasks_count,
        "total_users": total_users,
        "total_storage_bytes": total_storage_bytes,
        "queue_depth": queue_depth,
    }
