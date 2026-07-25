import asyncio
import httpx
from app.core.config import settings
from app.core.security import validate_url_is_safe
from app.core.exceptions import TargetTimeoutError, TargetUnreachableError

_semaphore = asyncio.Semaphore(settings.max_concurrent_fetches)


async def fetch_with_ssrf_guard(url: str) -> tuple[httpx.Response, list[str]]:
    """
    Fetches a URL manually following redirects, re-validating the SSRF
    guard on every hop. Returns (final_response, redirect_chain_urls).
    """
    redirect_chain: list[str] = []
    current_url = url

    async with _semaphore:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": "url-audit-service/1.0"},
        ) as client:
            try:
                for _ in range(settings.max_redirects + 1):
                    validate_url_is_safe(current_url)
                    response = await client.get(current_url)

                    if response.is_redirect:
                        redirect_chain.append(current_url)
                        next_url = str(response.next_request.url)
                        current_url = next_url
                        continue

                    return response, redirect_chain

                # Exceeded max redirects — treat final hop's response as-is
                return response, redirect_chain

            except httpx.TimeoutException as exc:
                raise TargetTimeoutError(
                    f"Target site did not respond within "
                    f"{int(settings.http_timeout_seconds * 1000)}ms"
                ) from exc
            except (httpx.ConnectError, httpx.ConnectTimeout,
                     httpx.RemoteProtocolError) as exc:
                raise TargetUnreachableError(
                    "Could not reach target host (DNS/connection/TLS error)"
                ) from exc
