import pytest
from pydantic import ValidationError

from app.schemas.request import AuditRequest
from app.core.config import settings


def test_valid_https_url_accepted():
    req = AuditRequest(url="https://example.com")
    assert str(req.url).startswith("https://example.com")


def test_valid_http_url_accepted():
    req = AuditRequest(url="http://example.com")
    assert str(req.url).startswith("http://example.com")


def test_missing_url_raises():
    with pytest.raises(ValidationError):
        AuditRequest()


def test_malformed_url_raises():
    with pytest.raises(ValidationError):
        AuditRequest(url="not-a-url")


def test_non_http_scheme_raises():
    with pytest.raises(ValidationError):
        AuditRequest(url="ftp://example.com")


def test_javascript_scheme_raises():
    with pytest.raises(ValidationError):
        AuditRequest(url="javascript:alert(1)")


def test_url_at_max_length_accepted():
    # "https://example.com/" + padding, kept just at the configured limit
    prefix = "https://example.com/"
    padding = "a" * (settings.max_url_length - len(prefix))
    url = prefix + padding
    assert len(url) == settings.max_url_length
    req = AuditRequest(url=url)
    assert str(req.url) == url


def test_url_exceeding_max_length_raises():
    prefix = "https://example.com/"
    padding = "a" * (settings.max_url_length - len(prefix) + 1)
    url = prefix + padding
    assert len(url) == settings.max_url_length + 1
    with pytest.raises(ValidationError):
        AuditRequest(url=url)
