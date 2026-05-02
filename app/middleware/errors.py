import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("agora.errors")


def _get_request_id(request: Request) -> str:
    """Return the request_id set by RequestLoggingMiddleware, or 'unknown'."""
    return getattr(request.state, "request_id", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the given FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning("request_id=%s | RequestValidationError: %s", request_id, exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "request_id": request_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning(
            "request_id=%s | HTTPException %d: %s",
            request_id,
            exc.status_code,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning("request_id=%s | ValueError: %s", request_id, exc)
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": str(exc),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from app.config import settings  # local import avoids circular deps at module load

        request_id = _get_request_id(request)
        logger.exception("request_id=%s | Unhandled exception: %s", request_id, exc)

        detail = str(exc) if settings.debug else "An unexpected error occurred."
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": detail,
                "request_id": request_id,
            },
        )
