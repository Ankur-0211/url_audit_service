from fastapi import APIRouter, Request
from app.schemas.request import AuditRequest
from app.schemas.response import AuditResponse
from app.services.audit_service import run_audit
from app.middleware.rate_limiter import rate_limiter
from app.core.exceptions import RateLimitExceededError

router = APIRouter()


@router.post("/audit", response_model=AuditResponse)
async def audit(payload: AuditRequest, request: Request):
    request_id = request.state.request_id

    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        raise RateLimitExceededError(
            f"Too many requests, retry after {int(retry_after) + 1}s",
            retry_after=retry_after,
        )

    result = await run_audit(str(payload.url), request_id)
    return result


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/")
async def root():
    return {"service": "url-audit-service", 
            "version": "1.0.0",
            "docs": "/docs",
            "credit": "Built for Digital Heroes Training Task",
            "credit_url": "https://digitaheroesco.com",
            }
