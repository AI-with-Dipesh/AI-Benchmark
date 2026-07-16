from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from aibenchmark.app.execution_policy import ExecutionPolicy
from aibenchmark.app.models import RoutingPlan


def _make_plan(provider="p1", model="m1", fallback_providers=None, fallback_models=None) -> RoutingPlan:
    return RoutingPlan(
        provider=provider,
        model=model,
        estimated_cost=0.0,
        rationale="",
        fallback_providers=fallback_providers or [],
        fallback_models=fallback_models or [],
    )


def _make_policy(routing: dict) -> ExecutionPolicy:
    policy = ExecutionPolicy.__new__(ExecutionPolicy)
    policy.config = SimpleNamespace(routing=routing)
    policy._registry = MagicMock()
    policy._health = MagicMock()
    policy._health.get.return_value = MagicMock(failure_rate=0.0)
    policy._cooldowns = {}
    return policy


def test_is_circuit_open_disabled_circuit():
    policy = _make_policy({"circuit_breaker": {"enabled": False}})
    assert policy.is_circuit_open("p1") is False


def test_is_circuit_open_in_cooldown():
    policy = _make_policy({"circuit_breaker": {"enabled": True, "cooldown_seconds": 10}})
    policy._cooldowns = {"p1": 9999.0}
    with patch("time.time", return_value=10000.0):
        assert policy.is_circuit_open("p1") is True


def test_is_circuit_open_failure_rate_exceeded():
    policy = _make_policy({"circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5}})
    policy._health.get.return_value = MagicMock(failure_rate=0.8)
    assert policy.is_circuit_open("p1") is True


def test_is_circuit_open_healthy():
    policy = _make_policy({"circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5}})
    policy._health.get.return_value = MagicMock(failure_rate=0.1)
    assert policy.is_circuit_open("p1") is False


def test_record_failure_updates_cooldown():
    policy = _make_policy({})
    with patch("time.time", return_value=1234.5):
        policy.record_failure("p1")
    assert policy._cooldowns["p1"] == 1234.5


def test_apply_fallback_disabled_returns_primary():
    policy = _make_policy({"fallback_enabled": False})
    plan = _make_plan()
    result = policy.apply(plan)
    assert result.provider == "p1"


def test_apply_with_fallback_chain():
    policy = _make_policy({
        "fallback_enabled": True,
        "fallback": {"strategy": "provider_first"},
        "fallback_chain": ["p1", "p2", "p3"],
    })
    policy._registry.get_plugin.side_effect = lambda name: object() if name in {"p2", "p3"} else None
    plan = _make_plan(provider="p1", fallback_providers=[])
    result = policy.apply(plan)
    assert "p2" in result.fallback_providers
    assert "p3" in result.fallback_providers


def test_next_provider_returns_first_open():
    policy = _make_policy({})
    plan = _make_plan(fallback_providers=["p2", "p3"])
    policy.is_circuit_open = MagicMock(side_effect=[True, False])
    assert policy.next_provider(plan) == "p3"


def test_next_provider_none_when_all_open():
    policy = _make_policy({})
    plan = _make_plan(fallback_providers=["p2", "p3"])
    policy.is_circuit_open = MagicMock(return_value=True)
    assert policy.next_provider(plan) is None


def test_execute_returns_status():
    policy = ExecutionPolicy.__new__(ExecutionPolicy)
    result = policy.execute({})
    assert result == {"status": "ok"}
