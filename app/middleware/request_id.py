import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging.logger import request_id_var, get_logger

logger = get_logger("url_audit_service.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns a request_id per request, stores it in a contextvar (so every
    log line emitted during this request picks it up automatically), and
    logs one line on request start and one on request completion —
    matching SDD §16.3/§16.4.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)

        client_ip = request.client.host if request.client else "unknown"
        start = time.monotonic()

        logger.info(
            "request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )

        request_id_var.reset(token)
        return response
