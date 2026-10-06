from typing import Protocol, Self


class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: object, *args: object) -> None: ...
