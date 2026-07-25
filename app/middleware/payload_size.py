from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import PayloadTooLargeError
from app.logging.logger import get_logger

logger = get_logger("url_audit_service.payload_size")


def _error_body(code: str, message: str, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": {},
        }
    }


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects oversized request bodies via the Content-Length header,
    before any body parsing happens — per SDD §13.3. Runs downstream of
    RequestIdMiddleware so request_id/logging are already in place.
    """

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = None

            if size is not None and size > settings.max_body_size_bytes:
                request_id = getattr(request.state, "request_id", "-")
                logger.warning(
                    "payload too large",
                    extra={
                        "content_length": size,
                        "max_body_size_bytes": settings.max_body_size_bytes,
                    },
                )
                exc = PayloadTooLargeError(
                    f"Request body exceeds maximum size of "
                    f"{settings.max_body_size_bytes} bytes"
                )
                return JSONResponse(
                    status_code=exc.status_code,
                    content=_error_body(exc.code, exc.message, request_id),
                )

        return await call_next(request)
