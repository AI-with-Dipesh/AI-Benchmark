from __future__ import annotations

from pathlib import Path

import pytest

from aibenchmark.app.config import AppConfig, ConfigError


def test_valid_fallback_strategy_values(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent.parent.parent / "configs"
    for value in ("provider_first", "model_first", "hybrid"):
        config = AppConfig(config_dir=base)
        config._load_routing({
            "strategy": "cost_aware",
            "fallback": {"strategy": value},
            "fallback_enabled": False,
            "fallback_chain": [],
            "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 300},
            "parallel": {"enabled": False, "max_workers": 4},
            "preference": {"prefer_free": False, "min_capability_score": 0.7},
        })
        assert config.routing["fallback"]["strategy"] == value


def test_invalid_fallback_strategy_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="routing.fallback.strategy"):
        AppConfig.__new__(AppConfig)._load_routing({
            "strategy": "cost_aware",
            "fallback": {"strategy": "unknown"},
            "fallback_enabled": False,
            "fallback_chain": [],
            "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 300},
            "parallel": {"enabled": False, "max_workers": 4},
            "preference": {"prefer_free": False, "min_capability_score": 0.7},
        })


def test_missing_fallback_strategy_defaults_to_provider_first(tmp_path: Path) -> None:
    app_config = AppConfig.__new__(AppConfig)
    app_config.routing = {}
    app_config._load_routing({
        "strategy": "cost_aware",
        "fallback_enabled": False,
        "fallback_chain": [],
        "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 300},
        "parallel": {"enabled": False, "max_workers": 4},
        "preference": {"prefer_free": False, "min_capability_score": 0.7},
    })
    assert app_config.routing["fallback"]["strategy"] == "provider_first"
