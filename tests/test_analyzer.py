import httpx

from app.services.analyzer import analyze_headers, analyze_html
from tests.conftest import SAMPLE_HTML


def test_analyze_html_extracts_title_meta_h1():
    result = analyze_html("text/html; charset=UTF-8", SAMPLE_HTML.encode())
    assert result["title"] == "Example Domain"
    assert result["meta_description"] == "An example page for testing."
    assert result["h1_count"] == 1


def test_analyze_html_missing_title_returns_none():
    html = "<html><body><h1>No title here</h1></body></html>"
    result = analyze_html("text/html", html.encode())
    assert result["title"] is None
    assert result["meta_description"] is None
    assert result["h1_count"] == 1


def test_analyze_html_multiple_h1_tags_counted():
    html = "<html><body><h1>One</h1><h1>Two</h1></body></html>"
    result = analyze_html("text/html", html.encode())
    assert result["h1_count"] == 2


def test_analyze_html_non_html_content_type_returns_defaults():
    result = analyze_html("application/json", b'{"foo": "bar"}')
    assert result == {"title": None, "meta_description": None, "h1_count": 0}


def test_analyze_html_none_content_type_returns_defaults():
    result = analyze_html(None, b"irrelevant")
    assert result == {"title": None, "meta_description": None, "h1_count": 0}


def test_analyze_headers_all_present():
    response = httpx.Response(
        200,
        headers={
            "strict-transport-security": "max-age=31536000",
            "content-security-policy": "default-src 'self'",
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
        },
    )
    result = analyze_headers(response)
    assert all(result.values())


def test_analyze_headers_none_present():
    response = httpx.Response(200, headers={})
    result = analyze_headers(response)
    assert not any(result.values())


def test_analyze_headers_partial():
    response = httpx.Response(
        200, headers={"x-frame-options": "DENY"}
    )
    result = analyze_headers(response)
    assert result["x_frame_options"] is True
    assert result["strict_transport_security"] is False
