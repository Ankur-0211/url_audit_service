import time
from datetime import datetime, timezone
from app.core.http_client import fetch_with_ssrf_guard
from app.core.config import settings
from app.services.analyzer import analyze_headers, analyze_html
from app.schemas.response import AuditResponse, SecurityHeaders
from app.cache.memory_cache import audit_cache
from app.utils.url_utils import normalize_url
from app.logging.logger import get_logger

logger = get_logger("url_audit_service.audit")


async def run_audit(url: str, request_id: str) -> AuditResponse:
    cache_key = normalize_url(url)
    cached_result = audit_cache.get(cache_key)

    if cached_result is not None:
        logger.info("audit cache hit", extra={"url": url, "cache_key": cache_key})
        return cached_result.model_copy(update={
            "cached": True,
            "request_id": request_id,
        })

    logger.info("audit cache miss", extra={"url": url, "cache_key": cache_key})

    start = time.monotonic()

    response, redirect_chain = await fetch_with_ssrf_guard(url)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    content_type = response.headers.get("content-type")

    html_fields = analyze_html(content_type, response.content)
    security_headers = analyze_headers(response)

    result = AuditResponse(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        reachable=True,
        response_time_ms=elapsed_ms,
        redirected=len(redirect_chain) > 0,
        redirect_chain=redirect_chain,
        content_type=content_type,
        content_length_bytes=len(response.content),
        title=html_fields["title"],
        meta_description=html_fields["meta_description"],
        h1_count=html_fields["h1_count"],
        security_headers=SecurityHeaders(**security_headers),
        cached=False,
        audited_at=datetime.now(timezone.utc),
        request_id=request_id,
    )

    logger.info(
        "audit completed",
        extra={
            "url": url,
            "final_url": result.final_url,
            "status_code": result.status_code,
            "response_time_ms": elapsed_ms,
            "redirected": result.redirected,
        },
    )

    audit_cache.set(cache_key, result, settings.cache_ttl_seconds)

    return result
