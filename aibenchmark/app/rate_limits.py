from __future__ import annotations

import logging
from typing import Any

from aibenchmark.app.models import RateLimitStatus

logger = logging.getLogger(__name__)


class RateLimitDetector:
    @staticmethod
    def from_status_code(status_code: int) -> RateLimitStatus:
        if status_code == 429:
            return RateLimitStatus(is_rate_limited=True)
        if status_code in (502, 503, 504):
            return RateLimitStatus(provider_maintenance=True)
        return RateLimitStatus()

    @staticmethod
    def from_headers(headers: dict[str, str], status_code: int) -> RateLimitStatus:
        rl = RateLimitStatus()
        if status_code == 429:
            rl = RateLimitStatus(is_rate_limited=True)
        for key in ("x-ratelimit-remaining", "x-ratelimit-limit", "x-ratelimit-reset", "retry-after", "x-ms-ratelimit-remaining"):
            val = headers.get(key, "").strip()
            if not val:
                continue
            try:
                if "remaining" in key.lower():
                    rl = rl.__class__(**dict(rl.__dict__, remaining=int(val)))
                elif "limit" in key.lower():
                    rl = rl.__class__(**dict(rl.__dict__, limit=int(val)))
                elif "reset" in key.lower():
                    rl = rl.__class__(**dict(rl.__dict__, reset_seconds=int(val)))
                elif key == "retry-after":
                    rl = rl.__class__(**dict(rl.__dict__, retry_after=int(val)))
            except ValueError:
                pass
        if rl.remaining == 0 or (rl.remaining is not None and rl.limit is not None and rl.remaining <= (rl.limit * 0.05)):
            rl = rl.__class__(**dict(rl.__dict__, is_rate_limited=True, burst_limit_hit=True))
        return rl

    @staticmethod
    def from_body(body: dict[str, Any]) -> RateLimitStatus:
        error = body.get("error", {}) if isinstance(body, dict) else {}
        message = error.get("message", "") if isinstance(error, dict) else ""
        message = str(message).lower()
        if "quota" in message or "billing" in message:
            return RateLimitStatus(quota_exceeded=True)
        if "daily" in message:
            return RateLimitStatus(daily_quota_exceeded=True)
        if "maintenance" in message or "temporarily unavailable" in message:
            return RateLimitStatus(provider_maintenance=True)
        if "rate limit" in message or "too many requests" in message:
            return RateLimitStatus(is_rate_limited=True)
        return RateLimitStatus()

    @staticmethod
    def detect(status_code: int, headers: dict[str, str], body: dict[str, Any] | None = None) -> RateLimitStatus:
        rl = RateLimitDetector.from_status_code(status_code)
        header_rl = RateLimitDetector.from_headers(headers, status_code)
        if body:
            body_rl = RateLimitDetector.from_body(body)
            rl = RateLimitStatus(
                is_rate_limited=rl.is_rate_limited or header_rl.is_rate_limited or body_rl.is_rate_limited,
                quota_exceeded=rl.quota_exceeded or header_rl.quota_exceeded or body_rl.quota_exceeded,
                provider_maintenance=rl.provider_maintenance or header_rl.provider_maintenance or body_rl.provider_maintenance,
                daily_quota_exceeded=rl.daily_quota_exceeded or header_rl.daily_quota_exceeded or body_rl.daily_quota_exceeded,
                burst_limit_hit=rl.burst_limit_hit or header_rl.burst_limit_hit or body_rl.burst_limit_hit,
                remaining=header_rl.remaining if header_rl.remaining is not None else (body_rl.remaining if body_rl.remaining is not None else rl.remaining),
                limit=header_rl.limit if header_rl.limit is not None else (body_rl.limit if body_rl.limit is not None else rl.limit),
                reset_seconds=header_rl.reset_seconds if header_rl.reset_seconds is not None else (body_rl.reset_seconds if body_rl.reset_seconds is not None else rl.reset_seconds),
                retry_after=header_rl.retry_after if header_rl.retry_after is not None else (body_rl.retry_after if body_rl.retry_after is not None else rl.retry_after),
                provider_specific_limits=rl.provider_specific_limits | header_rl.provider_specific_limits | body_rl.provider_specific_limits,
            )
        else:
            rl = RateLimitStatus(
                is_rate_limited=rl.is_rate_limited or header_rl.is_rate_limited,
                quota_exceeded=rl.quota_exceeded or header_rl.quota_exceeded,
                provider_maintenance=rl.provider_maintenance or header_rl.provider_maintenance,
                daily_quota_exceeded=rl.daily_quota_exceeded or header_rl.daily_quota_exceeded,
                burst_limit_hit=rl.burst_limit_hit or header_rl.burst_limit_hit,
                remaining=header_rl.remaining if header_rl.remaining is not None else rl.remaining,
                limit=header_rl.limit if header_rl.limit is not None else rl.limit,
                reset_seconds=header_rl.reset_seconds if header_rl.reset_seconds is not None else rl.reset_seconds,
                retry_after=header_rl.retry_after if header_rl.retry_after is not None else rl.retry_after,
                provider_specific_limits=rl.provider_specific_limits | header_rl.provider_specific_limits,
            )
        return rl
