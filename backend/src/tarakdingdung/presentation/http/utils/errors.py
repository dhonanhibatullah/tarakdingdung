from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.presentation.http.schemas.response import ErrorResponse

_GENERIC = "Something went wrong on our end. Please try again later."

DOMAIN_STATUS: dict[ErrorType, tuple[int, str, str]] = {
    ErrorType.NOT_FOUND: (404, "Not Found", ""),
    ErrorType.USERNAME_EXISTS: (409, "Already Exists", "This username is already taken."),
    ErrorType.ROLE_NAME_EXISTS: (409, "Already Exists", "A role with this name already exists."),
    ErrorType.PERMISSION_NAME_EXISTS: (409, "Already Exists",
                                       "A permission with this name already exists."),
    ErrorType.ROLE_PERMISSION_EXISTS: (409, "Already Exists",
                                       "This permission is already assigned to the role."),
    ErrorType.CONFLICT: (409, "Already Exists", ""),
    ErrorType.BAD_ARGS: (400, "Invalid Format", ""),
    ErrorType.VALIDATION: (400, "Invalid Format", ""),
    ErrorType.BAD_STATE: (412, "Invalid State", ""),
    ErrorType.FORBIDDEN: (403, "Access Denied", ""),
    ErrorType.UNAUTHORIZED: (401, "Unauthorized", ""),
    ErrorType.TOKEN_EXPIRED: (401, "Session Expired",
                              "Your session has expired. Please sign in again."),
    ErrorType.TOKEN_INVALID: (401, "Invalid Token",
                              "Your session is no longer valid. Please sign in again."),
    ErrorType.TIMEOUT: (504, "Request Timeout", "The request took too long. Please try again."),
    ErrorType.RATE_LIMITED: (429, "Too Many Requests",
                             "An upstream service is rate limiting us. Please try again later."),
    ErrorType.UPSTREAM: (502, "Upstream Error", "An upstream service returned an error."),
    ErrorType.UNIMPLEMENTED: (501, "Not Implemented", "This feature isn't available yet."),
    ErrorType.FAILURE: (500, "Internal Server Error", _GENERIC),
    ErrorType.UNKNOWN: (500, "Internal Server Error", _GENERIC),
}


def domain_error_response(err: DomainError) -> tuple[int, ErrorResponse]:
    status, title, override = DOMAIN_STATUS.get(err.type, (500, "Internal Server Error", _GENERIC))
    message = override or (err.message or _GENERIC)
    return status, ErrorResponse(error=title, message=message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_request: Request, exc: DomainError) -> JSONResponse:
        status, body = domain_error_response(exc)
        return JSONResponse(status_code=status, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        detail = errors[0]["msg"] if errors else "request body is invalid"
        return JSONResponse(status_code=400,
                            content=ErrorResponse(error="Invalid Format",
                                                  message=detail).model_dump())

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500,
                            content=ErrorResponse(error="Internal Server Error",
                                                  message=_GENERIC).model_dump())
