import secrets

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Security
from fastapi.security import APIKeyHeader

from core.config import Config
from core.exceptions import UnauthorizedError

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


@inject
async def require_api_key(
    config: FromDishka[Config],
    api_key: str | None = Security(api_key_header),
) -> None:
    if api_key is None or not secrets.compare_digest(api_key, config.api_key):
        raise UnauthorizedError('Неверный или отсутствующий X-API-Key')
