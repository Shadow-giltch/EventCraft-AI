from eventcraft.security.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_under_quota():
    limiter = InMemoryRateLimiter(requests_per_minute=3)
    assert limiter.is_allowed("192.168.1.1") is True
    assert limiter.is_allowed("192.168.1.1") is True
    assert limiter.is_allowed("192.168.1.1") is True
    # 4th request exceeds quota
    assert limiter.is_allowed("192.168.1.1") is False

    # Different IP is permitted
    assert limiter.is_allowed("10.0.0.1") is True
