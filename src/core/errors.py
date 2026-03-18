from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid or missing API key.") -> None:
        super().__init__(code="unauthorized", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Your plan does not allow this action.") -> None:
        super().__init__(code="forbidden", message=message, status_code=403)


class BadRequestError(AppError):
    def __init__(self, message: str = "Invalid request.") -> None:
        super().__init__(code="bad_request", message=message, status_code=400)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
        },
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "detail": str(exc),
        },
    )