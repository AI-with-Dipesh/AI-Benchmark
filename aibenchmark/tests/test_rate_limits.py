from __future__ import annotations


from aibenchmark.app.rate_limits import RateLimitDetector, RateLimitStatus


class TestRateLimitDetector:
    def test_from_status_code_429(self) -> None:
        rl = RateLimitDetector.from_status_code(429)
        assert rl.is_rate_limited is True

    def test_from_status_code_503(self) -> None:
        rl = RateLimitDetector.from_status_code(503)
        assert rl.provider_maintenance is True

    def test_from_headers_rate_limit(self) -> None:
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-limit": "100", "retry-after": "30"}
        rl = RateLimitDetector.from_headers(headers, 200)
        assert rl.is_rate_limited is True
        assert rl.retry_after == 30

    def test_from_body_quota(self) -> None:
        body = {"error": {"message": "You have exceeded your quota."}}
        rl = RateLimitDetector.from_body(body)
        assert rl.quota_exceeded is True

    def test_from_body_maintenance(self) -> None:
        body = {"error": {"message": "Provider under maintenance"}}
        rl = RateLimitDetector.from_body(body)
        assert rl.provider_maintenance is True

    def test_detect_combined(self) -> None:
        headers = {"x-ratelimit-remaining": "5", "x-ratelimit-limit": "100"}
        rl = RateLimitDetector.detect(429, headers, {"error": {"message": "Too many requests"}})
        assert rl.is_rate_limited is True

    def test_retry_recommendation_rate_limited(self) -> None:
        rl = RateLimitStatus(is_rate_limited=True)
        assert "Rate limited" in rl.retry_recommendation

    def test_retry_recommendation_maintenance(self) -> None:
        rl = RateLimitStatus(provider_maintenance=True)
        assert "maintenance" in rl.retry_recommendation.lower()

    def test_retry_recommendation_quota(self) -> None:
        rl = RateLimitStatus(quota_exceeded=True)
        assert "quota" in rl.retry_recommendation.lower()
