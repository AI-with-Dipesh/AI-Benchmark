from __future__ import annotations

from pathlib import Path
import pytest

from aibenchmark.app.config import AppConfig, ConfigError


def test_config_loads_providers_and_weights():
    config = AppConfig()
    assert "nvidia" in config.providers
    assert config.weight("latency") > 0


def test_missing_config_dir_raises():
    with pytest.raises(ConfigError):
        AppConfig(config_dir=Path("/nonexistent"))


def test_api_key_resolution(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    config = AppConfig()
    assert config.provider_config("nvidia")["api_key"] == "test-key"


def test_missing_api_key_warning(monkeypatch, caplog):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine
    engine = BenchEngine()
    with pytest.raises(ValueError):
        engine._init_provider("nvidia")
    assert "API key for provider 'nvidia' is missing" in caplog.text
