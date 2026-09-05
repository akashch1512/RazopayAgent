from sqlalchemy.ext.asyncio import (
    AsyncEngine as SQLAlchemyAsyncEngine,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession as SQLAlchemyAsyncSession,
)
from sqlalchemy.ext.asyncio import (
    async_sessionmaker as SQLAlchemyAsyncSessionmaker,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine as create_sqlalchemy_async_engine,
)

from src.config.manager import settings


class AsyncDatabase:
    def __init__(self) -> None:
        self.async_engine: SQLAlchemyAsyncEngine = create_sqlalchemy_async_engine(
            url=settings.DATABASE_URL,
            echo=settings.IS_DB_ECHO_LOG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_POOL_OVERFLOW,
        )
        self.async_session: SQLAlchemyAsyncSessionmaker[SQLAlchemyAsyncSession] = SQLAlchemyAsyncSessionmaker(
            bind=self.async_engine,
            expire_on_commit=settings.IS_DB_EXPIRE_ON_COMMIT,
        )

    @property
    def set_async_db_uri(self) -> str:
        return settings.DATABASE_URL


async_db: AsyncDatabase = AsyncDatabase()
