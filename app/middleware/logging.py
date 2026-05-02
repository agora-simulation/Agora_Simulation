import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agora.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging middleware with per-request UUID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.monotonic()

        logger.info(
            "request_id=%s | %s %s | incoming",
            request_id,
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "request_id=%s | %s %s | %d | %dms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response


class AgoraFormatter(logging.Formatter):
    """Formats log records in the project's house style:
    2026-04-29 12:00:00 | INFO | request_id=abc123 | GET /simulations/ | 200 | 45ms
    The formatter is generic — individual records carry the structured message.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"{ts} | {record.levelname} | {record.getMessage()}"
