from sqlalchemy import text

from app.db.session import engine


UPGRADES = [
    """
    alter table if exists download_tasks
    alter column object_size type bigint
    using object_size::bigint
    """,
]


def main() -> None:
    with engine.begin() as connection:
        for sql in UPGRADES:
            connection.execute(text(sql))
    print("Database upgrade completed")


if __name__ == "__main__":
    main()
