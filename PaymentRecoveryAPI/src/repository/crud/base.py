from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession


class BaseCRUDRepository:
    def __init__(self, async_session: SQLAlchemyAsyncSession) -> None:
        self.async_session = async_session
