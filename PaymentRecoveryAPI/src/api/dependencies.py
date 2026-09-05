import typing

import fastapi
from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.crud.base import BaseCRUDRepository
from src.repository.database import async_db

CRUDRepositoryType = typing.TypeVar("CRUDRepositoryType", bound=BaseCRUDRepository)


async def get_async_session() -> typing.AsyncGenerator[AsyncSession, None]:
    async with async_db.async_session() as session:
        yield session


def get_repository(
    repo_type: type[CRUDRepositoryType],
) -> typing.Callable[[AsyncSession], CRUDRepositoryType]:
    def _get_repo(
        async_session: AsyncSession = fastapi.Depends(get_async_session),
    ) -> CRUDRepositoryType:
        return repo_type(async_session=async_session)

    return _get_repo
