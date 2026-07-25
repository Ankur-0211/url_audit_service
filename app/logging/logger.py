import logging
import json
import sys
from contextvars import ContextVar

from app.core.config import settings

# Populated by the request-ID middleware for the duration of each request.
# Any log line emitted anywhere during that request's execution picks this
# up automatically via RequestIdFilter, with no need to pass it explicitly.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Fields already present on a standard LogRecord — used to detect "extra"
# fields passed via logger.info(..., extra={...}) so we can flatten them
# into the JSON output.
_STANDARD_RECORD_FIELDS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "request_id", "taskName",
}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS:
                continue
            log_obj[key] = value

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def configure_logging() -> None:
    """Configures the root logger once at app startup. Idempotent enough
    for our purposes (handlers are cleared before being re-added)."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())

    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # Don't drown request logs in httpx's own per-call debug noise.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
