import socket as _socket

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.rate_limiter import rate_limiter

_real_getaddrinfo = _socket.getaddrinfo


def _fake_getaddrinfo(host, *args, **kwargs):
    """
    Real DNS resolution for loopback/localhost (works offline, needed by
    the dedicated SSRF tests). Everything else resolves to a fixed public
    IP so tests never depend on real internet DNS being reachable in CI.
    """
    if host in ("127.0.0.1", "localhost", "::1"):
        return _real_getaddrinfo(host, *args, **kwargs)
    return [(_socket.AF_INET, _socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


@pytest.fixture(autouse=True)
def mock_dns(monkeypatch):
    """Applies to every test so no test needs real network DNS."""
    monkeypatch.setattr("app.core.security.socket.getaddrinfo", _fake_getaddrinfo)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    rate_limiter is a module-level singleton shared across the whole test
    session. Without this, tests would pollute each other's request counts
    and produce order-dependent failures.
    """
    with rate_limiter._lock:
        rate_limiter._requests.clear()
    yield
    with rate_limiter._lock:
        rate_limiter._requests.clear()


@pytest.fixture
def client():
    return TestClient(app)


SAMPLE_HTML = """
<html>
  <head>
    <title>Example Domain</title>
    <meta name="description" content="An example page for testing.">
  </head>
  <body>
    <h1>Example Domain</h1>
    <p>This is example content.</p>
  </body>
</html>
"""
