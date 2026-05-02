import os

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    queue = Queue(settings.rq_queue_name, connection=redis)
    worker_cls = SimpleWorker if os.getenv("RQ_WORKER_MODE", "fork") == "simple" else Worker
    worker = worker_cls([queue], connection=redis)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
