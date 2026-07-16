from __future__ import annotations

from pathlib import Path
import tempfile
import yaml

import pytest

from aibenchmark.app.config import AppConfig, ConfigError


def _write_config(tmp_path: Path, providers: dict, routing: dict) -> None:
    """Helper to write a minimal valid config set to tmp_path."""
    (tmp_path / "providers.yaml").write_text(
        yaml.safe_dump(providers), encoding="utf-8"
    )
    (tmp_path / "benchmark.yaml").write_text(
        yaml.safe_dump({"routing": routing}), encoding="utf-8"
    )


def test_invalid_routing_fallback_strategy():
    """Cover routing.fallback strategy validation error path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={"fallback": {"strategy": "invalid_strategy"}},
        )
        with pytest.raises(ConfigError, match="fallback.strategy"):
            AppConfig(config_dir=tmp_path)


def test_routing_parallel_validation():
    """Cover routing.parallel max_workers validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={"parallel": {"max_workers": 0}},
        )
        with pytest.raises(ConfigError, match="max_workers"):
            AppConfig(config_dir=tmp_path)


def test_invalid_routing_cost_ceiling():
    """Cover routing.cost_ceiling validation error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={"cost_ceiling": "not-a-number"},
        )
        with pytest.raises(ConfigError, match="cost_ceiling"):
            AppConfig(config_dir=tmp_path)


def test_min_capability_score_validation():
    """Cover preference.min_capability_score out-of-range validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={"preference": {"min_capability_score": 1.5}},
        )
        with pytest.raises(ConfigError, match="min_capability_score"):
            AppConfig(config_dir=tmp_path)


def test_fallback_not_a_dict():
    """Cover routing.fallback non-dict validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={"fallback": "invalid"},
        )
        with pytest.raises(ConfigError, match="fallback must be a mapping"):
            AppConfig(config_dir=tmp_path)


def test_provider_config_unknown():
    """Cover provider_config unknown provider error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        _write_config(
            tmp_path,
            providers={"defaults": {"default_provider": "x", "default_model": "y"}},
            routing={},
        )
        config = AppConfig(config_dir=tmp_path)
        with pytest.raises(ConfigError, match="Unknown provider"):
            config.provider_config("nonexistent_provider_xyz")
