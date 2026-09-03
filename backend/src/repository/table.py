import sqlalchemy
from sqlalchemy.orm import DeclarativeBase


class DBTable(DeclarativeBase):
    metadata: sqlalchemy.MetaData = sqlalchemy.MetaData()  # type: ignore


Base: type[DeclarativeBase] = DBTable
