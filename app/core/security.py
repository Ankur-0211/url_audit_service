import ipaddress
import socket
from urllib.parse import urlparse
from app.core.exceptions import UrlNotAllowedError

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}
BLOCKED_IPS = {"169.254.169.254"}


def _is_blocked_ip(ip_str: str) -> bool:
    if ip_str in BLOCKED_IPS:
        return True
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_url_is_safe(url: str) -> None:
    """
    Raises UrlNotAllowedError if the URL's hostname resolves to a
    disallowed IP range. Must be called before EVERY outbound fetch,
    including on each redirect hop.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise UrlNotAllowedError("URL has no resolvable hostname")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise UrlNotAllowedError(
            "The requested host resolves to a disallowed address range"
        )

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS failure is not an SSRF concern — let the HTTP client
        # surface this as TARGET_UNREACHABLE instead.
        return

    for family, _, _, _, sockaddr in resolved_ips:
        ip_str = sockaddr[0]
        if _is_blocked_ip(ip_str):
            raise UrlNotAllowedError(
                "The requested host resolves to a disallowed address range"
            )
