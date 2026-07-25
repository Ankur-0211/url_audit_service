import httpx

from tests.conftest import SAMPLE_HTML


def test_happy_path(client, respx_mock):
    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(
            200,
            content=SAMPLE_HTML.encode(),
            headers={"content-type": "text/html; charset=UTF-8"},
        )
    )

    response = client.post("/audit", json={"url": "https://example.com"})
    assert response.status_code == 200

    body = response.json()
    assert body["reachable"] is True
    assert body["status_code"] == 200
    assert body["cached"] is False
    assert body["title"] == "Example Domain"
    assert body["meta_description"] == "An example page for testing."
    assert body["h1_count"] == 1
    assert body["redirected"] is False
    assert body["redirect_chain"] == []
    assert body["security_headers"] == {
        "strict_transport_security": False,
        "content_security_policy": False,
        "x_content_type_options": False,
        "x_frame_options": False,
    }
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_cache_hit_on_second_identical_request(client, respx_mock):
    route = respx_mock.get("https://example.com/cache-test").mock(
        return_value=httpx.Response(
            200,
            content=SAMPLE_HTML.encode(),
            headers={"content-type": "text/html"},
        )
    )

    first = client.post("/audit", json={"url": "https://example.com/cache-test"})
    second = client.post("/audit", json={"url": "https://example.com/cache-test"})

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    # Only one real outbound call should have happened
    assert route.call_count == 1
    # But the request_id reflects each request, not the cached one
    assert first.json()["request_id"] != second.json()["request_id"]


def test_missing_url_field_returns_validation_error(client):
    response = client.post("/audit", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in response.json()["error"]


def test_malformed_url_returns_validation_error(client):
    response = client.post("/audit", json={"url": "not-a-url"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_non_http_scheme_rejected(client):
    response = client.post("/audit", json={"url": "ftp://example.com"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_localhost_hostname_blocked_by_ssrf_guard(client):
    response = client.post("/audit", json={"url": "http://localhost/"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "URL_NOT_ALLOWED"


def test_loopback_ip_blocked_by_ssrf_guard(client):
    response = client.post("/audit", json={"url": "http://127.0.0.1/"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "URL_NOT_ALLOWED"


def test_target_timeout_returns_408(client, respx_mock):
    respx_mock.get("https://slow.example.com").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    response = client.post("/audit", json={"url": "https://slow.example.com"})
    assert response.status_code == 408
    assert response.json()["error"]["code"] == "TARGET_TIMEOUT"


def test_target_unreachable_returns_502(client, respx_mock):
    respx_mock.get("https://unreachable.example.com").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    response = client.post("/audit", json={"url": "https://unreachable.example.com"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "TARGET_UNREACHABLE"


def test_rate_limit_exceeded_returns_429(client, respx_mock, monkeypatch):
    from app.middleware.rate_limiter import rate_limiter

    monkeypatch.setattr(rate_limiter, "_max_requests", 3)
    monkeypatch.setattr(rate_limiter, "_window_seconds", 60.0)

    respx_mock.get("https://example.com/rl-test").mock(
        return_value=httpx.Response(
            200, content=SAMPLE_HTML.encode(), headers={"content-type": "text/html"}
        )
    )

    for _ in range(3):
        r = client.post("/audit", json={"url": "https://example.com/rl-test"})
        assert r.status_code == 200

    fourth = client.post("/audit", json={"url": "https://example.com/rl-test"})
    assert fourth.status_code == 429
    assert fourth.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in fourth.headers
    assert int(fourth.headers["Retry-After"]) >= 1


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "url-audit-service"
    assert body["docs"] == "/docs"
    assert body["credit"] == "Built for Digital Heroes Training Task"
    assert body["credit_url"] == "https://digitaheroesco.com"
