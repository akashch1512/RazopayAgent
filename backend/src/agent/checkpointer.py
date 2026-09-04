"""
DB persistence for the agent's state, via LangGraph's own `AsyncPostgresSaver` -
no hand-rolled checkpoint tables. One thread per recovery case (`thread_id =
str(case_id)`), so re-running a case resumes its prior conversation/state
instead of starting cold.

Follows the same "fresh connection per task" philosophy as
`src.workers.runtime`: a Celery task's real cost is the agent/LLM call, so the
per-task connect overhead here is irrelevant, and it avoids owning a
long-lived pool across tasks in a worker process.
"""

import contextlib
import typing

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config.manager import settings

# Guards against re-running the (idempotent, but not free) `setup()` call on
# every single task in a long-lived worker process - but only within *this*
# process; see `_ensure_schema` for the cross-process guard.
_schema_ready = False

# Arbitrary, fixed bigint for `pg_advisory_lock` - must be a stable literal,
# not `hash()` (Python randomizes string hashing per-process, which would
# defeat a *shared* lock key entirely).
_SETUP_LOCK_KEY = 782_341_009_215_667


async def _ensure_schema(saver: AsyncPostgresSaver) -> None:
    """
    `AsyncPostgresSaver.setup()` reads the applied-migrations table and then
    runs whatever is missing - with no locking of its own. On a cold start,
    every worker process's first task calls this at roughly the same time; two
    of them both seeing "no migrations applied yet" collide on `CREATE TYPE`
    (observed as a `UniqueViolation` on `pg_type_typname_nsp_index`). A
    Postgres advisory lock serializes that one-time setup across every worker
    process without needing a separate deploy-time migration step.
    """
    async with await psycopg.AsyncConnection.connect(settings.CHECKPOINTER_DATABASE_URL) as lock_conn:
        await lock_conn.execute("SELECT pg_advisory_lock(%s)", (_SETUP_LOCK_KEY,))
        try:
            await saver.setup()
        finally:
            await lock_conn.execute("SELECT pg_advisory_unlock(%s)", (_SETUP_LOCK_KEY,))


@contextlib.asynccontextmanager
async def get_checkpointer() -> typing.AsyncIterator[AsyncPostgresSaver]:
    global _schema_ready

    async with AsyncPostgresSaver.from_conn_string(settings.CHECKPOINTER_DATABASE_URL) as saver:
        if not _schema_ready:
            await _ensure_schema(saver)
            _schema_ready = True
        yield saver
