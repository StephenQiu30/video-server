from sqlalchemy import Engine, text


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
    "alter table if exists download_tasks add column if not exists retry_of_task_id varchar(36)",
    "alter table if exists download_tasks add column if not exists attempt_no integer not null default 1",
    "create index if not exists ix_download_tasks_retry_of_task_id on download_tasks (retry_of_task_id)",
    """
    do $$
    begin
        alter table download_tasks
        add constraint fk_download_tasks_retry_of_task_id
        foreign key (retry_of_task_id) references download_tasks(id);
    exception
        when duplicate_object then null;
        when undefined_table then null;
    end $$;
    """,
    """
    update download_tasks child
    set retry_of_task_id = parent_event.task_id
    from task_events parent_event
    where parent_event.message like '已创建重试任务：%'
      and child.id = substring(parent_event.message from '已创建重试任务：([0-9a-fA-F-]{36})')
      and child.retry_of_task_id is null
    """,
    """
    with recursive retry_chain as (
        select id, retry_of_task_id, 1 as depth
        from download_tasks
        where retry_of_task_id is null
        union all
        select child.id, child.retry_of_task_id, retry_chain.depth + 1
        from download_tasks child
        join retry_chain on child.retry_of_task_id = retry_chain.id
    )
    update download_tasks task
    set attempt_no = retry_chain.depth
    from retry_chain
    where task.id = retry_chain.id
    """,
    "alter table if exists download_tasks add column if not exists ai_summary text",
    "alter table if exists download_tasks add column if not exists ai_mindmap text",
    "alter table if exists download_tasks add column if not exists ai_status varchar(32)",
    "alter table if exists download_tasks add column if not exists ai_error text",
    "create index if not exists ix_download_tasks_ai_status on download_tasks (ai_status)",
    "alter table if exists users add column if not exists github_id varchar(100)",
    "alter table if exists users add column if not exists avatar_url varchar(500)",
    "alter table if exists users alter column password_hash drop not null",
    "create unique index if not exists ix_users_github_id on users (github_id)",
]


def run_database_upgrades(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        for sql in UPGRADES:
            connection.execute(text(sql))
