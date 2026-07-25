class AuditError(Exception):
    """Base class for all structured audit errors."""
    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(AuditError):
    code = "VALIDATION_ERROR"
    status_code = 422


class UrlNotAllowedError(AuditError):
    code = "URL_NOT_ALLOWED"
    status_code = 403


class TargetTimeoutError(AuditError):
    code = "TARGET_TIMEOUT"
    status_code = 408


class TargetUnreachableError(AuditError):
    code = "TARGET_UNREACHABLE"
    status_code = 502


class PayloadTooLargeError(AuditError):
    code = "PAYLOAD_TOO_LARGE"
    status_code = 413


class RateLimitExceededError(AuditError):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after
