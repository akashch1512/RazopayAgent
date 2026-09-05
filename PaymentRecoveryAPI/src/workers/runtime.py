"""
Async DB access for the worker process.

Celery tasks are synchronous, but our repositories (and, later, the LangGraph
agent) are async. Rather than duplicate every query in a sync flavour we run the
coroutine on a private event loop per task via `run_async`.

The engine uses `NullPool`: every task gets a fresh connection that is closed
when the task's loop ends, so there is no pool bound to a dead loop. For a
single-concurrency queue whose real cost is a multi-second agent call, the
per-task connect overhead is irrelevant.
"""

import asyncio
import contextlib
import typing

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config.manager import settings

_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.IS_DB_ECHO_LOG,
    poolclass=NullPool,
)
_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
)

T = typing.TypeVar("T")


def run_async(coro: typing.Coroutine[typing.Any, typing.Any, T]) -> T:
    """Execute `coro` to completion on a throwaway event loop."""
    return asyncio.run(coro)


@contextlib.asynccontextmanager
async def worker_session() -> typing.AsyncIterator[AsyncSession]:
    """A committed-or-rolled-back session scope for use inside a task."""
    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
