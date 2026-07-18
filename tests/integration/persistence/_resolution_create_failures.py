"""PostgreSQL failure injection for resolution-create writer tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text

_SEQUENCE = "test_resolution_create_serialization_attempt"
_FUNCTION = "test_fail_resolution_create_serialization"
_TRIGGER = "tr_test_fail_resolution_create_serialization"


@contextmanager
def fail_outbox_with_serialization(
    engine: Engine,
    *,
    failures: int,
) -> Iterator[Callable[[], int]]:
    if failures < 1:
        raise ValueError("failures must be positive")
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SEQUENCE {_SEQUENCE}"))
        connection.execute(
            text(
                f"""
                CREATE FUNCTION {_FUNCTION}() RETURNS trigger LANGUAGE plpgsql AS $$
                DECLARE attempt bigint;
                BEGIN
                    attempt := nextval('{_SEQUENCE}');
                    IF attempt <= {failures} THEN
                        RAISE EXCEPTION 'injected serialization failure'
                            USING ERRCODE = '40001';
                    END IF;
                    RETURN NEW;
                END; $$;
                CREATE TRIGGER {_TRIGGER} BEFORE INSERT ON outbox_messages
                FOR EACH ROW EXECUTE FUNCTION {_FUNCTION}();
                """
            )
        )

    active = True
    last_attempt = 0

    def attempt_count() -> int:
        if not active:
            return last_attempt
        with engine.connect() as connection:
            return int(connection.scalar(text(f"SELECT last_value FROM {_SEQUENCE}")) or 0)

    try:
        yield attempt_count
    finally:
        last_attempt = attempt_count()
        with engine.begin() as connection:
            connection.execute(text(f"DROP TRIGGER {_TRIGGER} ON outbox_messages"))
            connection.execute(text(f"DROP FUNCTION {_FUNCTION}()"))
            connection.execute(text(f"DROP SEQUENCE {_SEQUENCE}"))
        active = False
