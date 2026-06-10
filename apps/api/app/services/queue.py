from redis import Redis
from rq import Queue

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


def enqueue_download_task(task_id: str) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url)
        queue = Queue(settings.rq_queue_name, connection=redis)
        queue.enqueue(
            "worker.jobs.process_download_task",
            task_id,
            job_timeout=settings.max_task_runtime_seconds + 60,
            result_ttl=3600,
            failure_ttl=86400,
        )
    except Exception as exc:
        raise AppError(ErrorCode.QUEUE_UNAVAILABLE, "任务队列暂不可用，请稍后重试", 503) from exc

