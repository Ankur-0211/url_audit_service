import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import AuditError, RateLimitExceededError
from app.logging.logger import get_logger

logger = get_logger("url_audit_service.errors")


def _error_body(code: str, message: str, request_id: str, details: dict | None = None):
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        }
    }


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "rate limit exceeded",
            extra={"client_ip": client_ip, "retry_after": exc.retry_after},
        )
        response = JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, request_id, exc.details),
        )
        response.headers["Retry-After"] = str(int(exc.retry_after) + 1)
        return response

    @app.exception_handler(AuditError)
    async def audit_error_handler(request: Request, exc: AuditError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        logger.log(
            log_level,
            exc.message,
            extra={"error_code": exc.code, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, request_id, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        first_error = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        logger.warning(
            "validation error",
            extra={"field": field, "detail": first_error.get("msg", "invalid input")},
        )
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_ERROR",
                f"{field}: {first_error.get('msg', 'invalid input')}",
                request_id,
                {"field": field},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                request_id,
            ),
        )
