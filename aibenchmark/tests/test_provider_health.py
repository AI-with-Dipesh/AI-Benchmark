from __future__ import annotations

import pytest

from aibenchmark.app.provider_health import HealthTracker, reset_health_tracker, get_health_tracker
from aibenchmark.app.models import ProviderStatus
from aibenchmark.app.provider_registry import ProviderRegistry


class TestHealthTracker:
    def test_record_success_updates_average(self) -> None:
        tracker = HealthTracker(window_size=100)
        h = tracker.record("p1", 100.0, True)
        assert h.average_latency_ms == pytest.approx(100.0)
        assert h.failure_rate == pytest.approx(0.0)
        h2 = tracker.record("p1", 200.0, True)
        assert h2.average_latency_ms == pytest.approx(150.0)

    def test_record_failure_increases_failure_rate(self) -> None:
        tracker = HealthTracker(window_size=100)
        tracker.record("p1", 100.0, True)
        h = tracker.record("p1", 200.0, False)
        assert h.failure_rate == pytest.approx(0.5)

    def test_record_updates_p95_p99(self) -> None:
        tracker = HealthTracker(window_size=1000)
        for i in range(100):
            tracker.record("p1", float(i), True)
        h = tracker.get("p1")
        assert h.p95_latency_ms is not None
        assert h.p99_latency_ms is not None
        assert h.p95_latency_ms <= h.p99_latency_ms

    def test_window_size_limits_samples(self) -> None:
        tracker = HealthTracker(window_size=10)
        for i in range(100):
            tracker.record("p1", float(i), True)
        assert tracker.get("p1").total_checks == 100

    def test_get_returns_empty_for_unknown(self) -> None:
        tracker = HealthTracker()
        h = tracker.get("unknown")
        assert h.provider_name == "unknown"
        assert h.status == ProviderStatus.UNKNOWN

    def test_all_returns_dict(self) -> None:
        tracker = HealthTracker()
        tracker.record("p1", 100.0, True)
        all_h = tracker.all()
        assert "p1" in all_h

    def test_status_degraded_on_high_failure(self) -> None:
        tracker = HealthTracker()
        for _ in range(10):
            tracker.record("p1", 100.0, False)
        assert tracker.get("p1").status == ProviderStatus.UNAVAILABLE

    def test_p95_p99_none_when_empty(self) -> None:
        tracker = HealthTracker()
        from collections import deque
        assert tracker._p95(deque()) is None

    def test_record_retry_increments_retry_rate(self) -> None:
        reset_health_tracker()
        tracker = get_health_tracker()
        # 4 successes
        for _ in range(4):
            tracker.record("p1", 100.0, True)
        # 1 retry
        h = tracker.record("p1", 120.0, True, is_retry=True)
        assert h.retry_rate == pytest.approx(0.2)
        assert h.retry_rate == pytest.approx(1.0 / 5)

    def test_global_tracker_shared_between_registries(self) -> None:
        reset_health_tracker()
        r1 = ProviderRegistry()
        r2 = ProviderRegistry()
        assert r1.health_tracker is r2.health_tracker is get_health_tracker()
        r1.health_tracker.record("p1", 50.0, True)
        assert r2.health_tracker.get("p1").average_latency_ms == pytest.approx(50.0)
