def test_oversized_payload_returns_413(client):
    from app.core.config import settings

    # Padding field is ignored by pydantic (extra fields default to
    # "ignore"), but it inflates Content-Length past the limit — the
    # middleware rejects on the header alone, before any JSON parsing
    # or field validation happens.
    oversized_padding = "x" * (settings.max_body_size_bytes + 1000)
    response = client.post(
        "/audit",
        json={"url": "https://example.com", "padding": oversized_padding},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "request_id" in response.json()["error"]


def test_request_id_header_present_on_413(client):
    from app.core.config import settings

    oversized_padding = "x" * (settings.max_body_size_bytes + 1000)
    response = client.post(
        "/audit",
        json={"url": "https://example.com", "padding": oversized_padding},
    )

    assert response.status_code == 413
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]


def test_normal_sized_payload_not_rejected(client, respx_mock):
    import httpx
    from tests.conftest import SAMPLE_HTML

    respx_mock.get("https://example.com/normal-size").mock(
        return_value=httpx.Response(
            200, content=SAMPLE_HTML.encode(), headers={"content-type": "text/html"}
        )
    )

    response = client.post(
        "/audit", json={"url": "https://example.com/normal-size"}
    )
    assert response.status_code == 200
