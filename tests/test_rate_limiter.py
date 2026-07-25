import time

from app.middleware.rate_limiter import SlidingWindowRateLimiter


def test_requests_within_limit_are_allowed():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        allowed, retry_after = limiter.check("1.2.3.4")
        assert allowed is True
        assert retry_after == 0.0


def test_nth_plus_one_request_is_denied():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("1.2.3.4")

    allowed, retry_after = limiter.check("1.2.3.4")
    assert allowed is False
    assert retry_after > 0


def test_different_ips_have_independent_limits():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    allowed_a, _ = limiter.check("1.1.1.1")
    allowed_b, _ = limiter.check("2.2.2.2")
    assert allowed_a is True
    assert allowed_b is True


def test_requests_allowed_again_after_window_expires():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=0.05)
    allowed_first, _ = limiter.check("1.2.3.4")
    assert allowed_first is True

    denied, _ = limiter.check("1.2.3.4")
    assert denied is False

    time.sleep(0.1)
    allowed_after_wait, _ = limiter.check("1.2.3.4")
    assert allowed_after_wait is True
