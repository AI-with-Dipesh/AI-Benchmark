from __future__ import annotations

from typing import Any

import pytest

from aibenchmark.app.provider_health import HealthTracker
from aibenchmark.app.models import ProviderStatus, RateLimitStatus


def _record_sequence(tracker: HealthTracker, provider: str, events: list[Any]) -> None:
    for item in events:
        tracker.record(provider, item[0], item[1], item[2])  # type: ignore[arg-type]


class TestFailureRecoveryScenarios:
    def test_scenario_repeated_successes(self) -> None:
        tracker = HealthTracker(window_size=50)
        events = [(100.0 + i, True, None) for i in range(10)]
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.status == ProviderStatus.AVAILABLE
        assert h.availability == pytest.approx(1.0)
        assert h.failure_rate == pytest.approx(0.0)
        assert h.total_checks == 10
        assert h.p95_latency_ms is not None
        assert h.p99_latency_ms is not None
        assert h.timeout_rate == pytest.approx(0.0)
        assert h.retry_rate == pytest.approx(0.0)

    def test_scenario_intermittent_failures(self) -> None:
        tracker = HealthTracker(window_size=50)
        events = [(100.0, True, None), (200.0, False, None), (300.0, True, None), (400.0, False, None), (500.0, False, None)]
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.failure_rate == pytest.approx(3 / 5)
        assert h.availability == pytest.approx(2 / 5)
        assert h.status == ProviderStatus.UNAVAILABLE  # >= 50%

    def test_scenario_complete_outage(self) -> None:
        tracker = HealthTracker(window_size=50)
        events = [(100.0, False, None)] * 20
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.failure_rate == pytest.approx(1.0)
        assert h.availability == pytest.approx(0.0)
        assert h.status == ProviderStatus.UNAVAILABLE

    def test_scenario_recovery_after_outage(self) -> None:
        tracker = HealthTracker(window_size=50)
        # initial degraded state
        events1 = [(100.0, False)] * 4 + [(200.0, True)]
        _record_sequence(tracker, "p", [(lat, ok, None) for lat, ok in events1])
        h1 = tracker.get("p")
        assert h1.failure_rate == pytest.approx(4 / 5)

        # add successes to recover below 10% threshold
        events2 = [(150.0, True, None)] * 50
        _record_sequence(tracker, "p", events2)
        h2 = tracker.get("p")
        # failure_rate = 4/55
        assert h2.failure_rate == pytest.approx(4 / 55)
        assert h2.status == ProviderStatus.AVAILABLE
        assert h2.availability == pytest.approx(51 / 55)

    def test_scenario_rate_limited_provider(self) -> None:
        tracker = HealthTracker(window_size=50)
        rl = RateLimitStatus(is_rate_limited=True, remaining=0)
        events = [(100.0, True, None), (200.0, True, None), (50.0, True, rl), (300.0, False, None)]
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.status == ProviderStatus.DEGRADED
        # 1 failure out of 4 with rate-limit event initially flagged
        assert h.failure_rate == pytest.approx(0.25)
        assert h.availability == pytest.approx(0.75)

    def test_scenario_slow_provider(self) -> None:
        tracker = HealthTracker(window_size=50)
        events = [(5000.0, True, None)] * 30
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.average_latency_ms == pytest.approx(5000.0)
        assert h.p95_latency_ms == pytest.approx(5000.0)
        assert h.p99_latency_ms == pytest.approx(5000.0)
        assert h.status == ProviderStatus.AVAILABLE

    def test_scenario_slow_then_fast(self) -> None:
        tracker = HealthTracker(window_size=300)
        # ratio: many fast samples so p95/p99 fall into the fast tail, but window must preserve slow tail
        events = [(8000.0, True, None)] * 5 + [(100.0, True, None)] * 200
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.average_latency_ms == pytest.approx((5 * 8000 + 200 * 100) / 205)
        assert h.p95_latency_ms is not None
        assert h.p99_latency_ms is not None
        assert h.p95_latency_ms < h.p99_latency_ms  # ordering invariant

    def test_scenario_window_trims_correctly(self) -> None:
        tracker = HealthTracker(window_size=10)
        # 50 failures all at once
        events = [(10.0 + i, False, None) for i in range(50)]
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.total_checks == 50
        # samples deque keeps last 10, all false → 100% failure
        assert h.failure_rate == pytest.approx(1.0)
        assert h.status == ProviderStatus.UNAVAILABLE

    def test_scenario_timeout_rate_tracked(self) -> None:
        tracker = HealthTracker(window_size=50)
        # HealthTracker doesn't natively track timeout/retry from record args;
        # verify zero defaults and that repeated record keeps them at 0
        events = [(100.0, True)] * 10
        _record_sequence(tracker, "p", [(lat, ok, None) for lat, ok in events])
        h = tracker.get("p")
        assert h.timeout_rate == pytest.approx(0.0)
        assert h.retry_rate == pytest.approx(0.0)

    def test_scenario_success_failure_success_transitions(self) -> None:
        tracker = HealthTracker(window_size=50)
        # success → failure → success verifies status transitions
        tracker.record("p", 100.0, True)
        assert tracker.get("p").status == ProviderStatus.AVAILABLE
        tracker.record("p", 100.0, False)
        assert tracker.get("p").status == ProviderStatus.UNAVAILABLE  # 1/2 = 0.5
        tracker.record("p", 100.0, True)
        # 1/3 failure rate = 0.333 → DEGRADED (>= 10% threshold)
        assert tracker.get("p").status == ProviderStatus.DEGRADED  # 1/3

    def test_scenario_zero_latency_accepted(self) -> None:
        tracker = HealthTracker(window_size=50)
        h = tracker.record("p", 0.0, True)
        assert h.average_latency_ms == pytest.approx(0.0)
        assert h.p95_latency_ms == pytest.approx(0.0)
        assert h.p99_latency_ms == pytest.approx(0.0)

    def test_scenario_end_to_end_golden_sequence(self) -> None:
        tracker = HealthTracker(window_size=1000)
        events = [
            (255.0, True, None),
            (275.0, True, None),
            (250.0, False, None),  # timeout-ish
            (260.0, True, None),
            (290.0, True, None),
            (245.0, False, None),
            (270.0, False, None),
            (280.0, True, None),
            (230.0, True, None),
            (235.0, True, None),
            (300.0, True, None),
        ]
        _record_sequence(tracker, "p", events)
        h = tracker.get("p")
        assert h.total_checks == 11
        assert h.failure_rate == pytest.approx(3 / 11)
        assert h.status == ProviderStatus.DEGRADED  # fail >= 10% but < 50%
        assert h.availability == pytest.approx(8 / 11)
        assert h.p95_latency_ms is not None
        assert h.p99_latency_ms is not None

    def test_scenario_multiple_providers_independent(self) -> None:
        tracker = HealthTracker(window_size=50)
        tracker.record("a", 100.0, True)
        tracker.record("a", 400.0, False)
        tracker.record("b", 200.0, True)
        tracker.record("b", 300.0, True)
        a = tracker.get("a")
        b = tracker.get("b")
        assert a.failure_rate == pytest.approx(0.5)
        assert b.failure_rate == pytest.approx(0.0)
        assert a.status == ProviderStatus.UNAVAILABLE
        assert b.status == ProviderStatus.AVAILABLE
