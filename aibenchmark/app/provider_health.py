from __future__ import annotations

import logging
import time
from collections import deque

from aibenchmark.app.models import ProviderHealth, ProviderStatus, RateLimitStatus

logger = logging.getLogger(__name__)


class HealthTracker:
    def __init__(self, window_size: int = 1000) -> None:
        self.window_size = window_size
        self._samples: dict[str, deque[float]] = {}
        self._states: dict[str, ProviderHealth] = {}

    def record(self, provider_name: str, latency_ms: float, success: bool, rate_limit: RateLimitStatus | None = None, *, is_timeout: bool = False, is_retry: bool = False) -> ProviderHealth:
        samples = self._samples.setdefault(provider_name, deque(maxlen=self.window_size))
        samples.append(latency_ms)
        prev = self._states.get(provider_name)
        total = (prev.total_checks if prev else 0) + 1
        prev_avg: float = prev.average_latency_ms if prev and prev.average_latency_ms is not None else 0.0
        prev_fail: float = prev.failure_rate if prev else 0.0
        prev_timeout_rate: float = prev.timeout_rate if prev else 0.0
        prev_retry_rate: float = prev.retry_rate if prev else 0.0
        avg = ((prev_avg * (total - 1)) + latency_ms) / total
        _sorted = sorted(samples)
        median = _sorted[len(_sorted) // 2] if len(_sorted) % 2 == 1 else (_sorted[len(_sorted) // 2 - 1] + _sorted[len(_sorted) // 2]) / 2.0
        fail = ((prev_fail * (total - 1)) + (0.0 if success else 1.0)) / total
        timeout_rate = ((prev_timeout_rate * (total - 1)) + (1.0 if is_timeout else 0.0)) / total
        retry_rate = ((prev_retry_rate * (total - 1)) + (1.0 if is_retry else 0.0)) / total
        rl = rate_limit or RateLimitStatus()
        last_check = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if fail >= 0.5:
            status = ProviderStatus.UNAVAILABLE
        elif fail >= 0.1 or rl.is_rate_limited or rl.quota_exceeded:
            status = ProviderStatus.DEGRADED
        elif total > 0 and fail < 0.1:
            status = ProviderStatus.AVAILABLE
        else:
            status = ProviderStatus.UNKNOWN
        self._states[provider_name] = ProviderHealth(
            provider_name=provider_name,
            status=status,
            availability=1.0 - fail,
            authentication_status=True,
            connection_health=success,
            average_latency_ms=avg,
            median_latency_ms=median,
            p95_latency_ms=self._p95(samples),
            p99_latency_ms=self._p99(samples),
            failure_rate=fail,
            timeout_rate=timeout_rate,
            retry_rate=retry_rate,
            total_checks=total,
            last_check=last_check,
            rate_limit=rl,
        )
        return self._states[provider_name]

    def get(self, provider_name: str) -> ProviderHealth:
        return self._states.get(provider_name, ProviderHealth(provider_name=provider_name))

    def all(self) -> dict[str, ProviderHealth]:
        return dict(self._states)

    def _p95(self, samples: deque[float]) -> float | None:
        return self._percentile(samples, 95)

    def _p99(self, samples: deque[float]) -> float | None:
        return self._percentile(samples, 99)

    @staticmethod
    def _percentile(samples: deque[float], pct: float) -> float | None:
        if not samples:
            return None
        ordered = sorted(samples)
        k = (len(ordered) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(ordered):
            return float(ordered[f])
        return float(ordered[f] + (ordered[c] - ordered[f]) * (k - f))


_global_tracker = HealthTracker()


def get_health_tracker() -> HealthTracker:
    return _global_tracker


def reset_health_tracker() -> None:
    global _global_tracker
    _global_tracker = HealthTracker()
