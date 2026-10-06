from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyUOW:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()
