import typing

import fastapi
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.api.dependencies.session import get_async_session
from src.repository.crud.base import BaseCRUDRepository

CRUDRepositoryType = typing.TypeVar("CRUDRepositoryType", bound=BaseCRUDRepository)


def get_repository(
    repo_type: type[CRUDRepositoryType],
) -> typing.Callable[[SQLAlchemyAsyncSession], CRUDRepositoryType]:
    def _get_repo(
        async_session: SQLAlchemyAsyncSession = fastapi.Depends(get_async_session),
    ) -> CRUDRepositoryType:
        return repo_type(async_session=async_session)

    return _get_repo
