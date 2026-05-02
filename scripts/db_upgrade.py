from sqlalchemy import text

from app.db.session import engine


UPGRADES = [
    """
    alter table if exists download_tasks
    alter column object_size type bigint
    using object_size::bigint
    """,
    "alter table if exists users add column if not exists is_admin boolean not null default false",
    "alter table if exists users add column if not exists daily_task_quota integer not null default 10",
    "alter table if exists users add column if not exists concurrent_task_quota integer not null default 1",
    "alter table if exists users add column if not exists max_file_size_bytes bigint not null default 2147483648",
    "alter table if exists users add column if not exists file_retention_hours integer not null default 24",
    "alter table if exists users add column if not exists storage_quota_bytes bigint not null default 5368709120",
]


def main() -> None:
    with engine.begin() as connection:
        for sql in UPGRADES:
            connection.execute(text(sql))
    print("Database upgrade completed")


if __name__ == "__main__":
    main()
