from redis import Redis
from rq import Queue, Worker

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(settings.rq_queue_name, connection=redis)], connection=redis)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

