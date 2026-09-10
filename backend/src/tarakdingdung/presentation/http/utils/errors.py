from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tarakdingdung.domain.models.error import DomainError, ErrorType

_STATUS: dict[ErrorType, int] = {
    ErrorType.VALIDATION: 400,
    ErrorType.BAD_ARGS: 400,
    ErrorType.NOT_FOUND: 404,
    ErrorType.UNAUTHORIZED: 401,
    ErrorType.FORBIDDEN: 403,
    ErrorType.CONFLICT: 409,
    ErrorType.INTERNAL: 500,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=_STATUS.get(exc.error_type, 500),
            content={"detail": exc.message},
        )
