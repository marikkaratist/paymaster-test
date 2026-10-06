from enum import StrEnum


class ErrorCode(StrEnum):
    NOT_FOUND = 'not_found'
    CONFLICT = 'conflict'
    UNAUTHORIZED = 'unauthorized'
    INTERNAL = 'internal'


class DomainError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = ErrorCode.NOT_FOUND


class IdempotencyConflictError(DomainError):
    code = ErrorCode.CONFLICT


class UnauthorizedError(DomainError):
    code = ErrorCode.UNAUTHORIZED


class AdapterError(DomainError):
    code = ErrorCode.INTERNAL


class WebhookDeliveryError(AdapterError):
    pass
