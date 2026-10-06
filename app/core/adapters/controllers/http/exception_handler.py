from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from core.adapters.controllers.http.schema import ErrorResponse
from core.exceptions import DomainError, ErrorCode
from core.logger import get_logger

logger = get_logger(__name__)

STATUS_BY_CODE = {
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    if exc.code == ErrorCode.INTERNAL:
        logger.error('domain error', message=exc.message)
    body = ErrorResponse(code=exc.code.value, message=exc.message)
    return JSONResponse(body.model_dump(), status_code=STATUS_BY_CODE[exc.code])


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
