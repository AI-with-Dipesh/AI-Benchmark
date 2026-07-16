from __future__ import annotations

import os
from pathlib import Path
import tempfile


from aibenchmark.app.auth import CredentialResolver


def test_resolve_missing_provider_returns_empty():
    resolver = CredentialResolver({})
    assert resolver.resolve("missing") == ""


def test_resolve_non_dict_config_returns_empty():
    resolver = CredentialResolver({"bad": "not-a-dict"})
    assert resolver.resolve("bad") == ""


def test_validate_non_dict_provider_config():
    resolver = CredentialResolver({"p": "not-a-dict"})
    result = resolver.validate("p")
    assert result.authenticated is False
    assert "not configured" in result.message


def test_validate_empty_api_key_returns_missing():
    resolver = CredentialResolver({"p": {"api_key_env": "MISSING_KEY"}})
    result = resolver.validate("p")
    assert result.authenticated is False
    assert "MISSING_KEY" in result.message


def test_validate_sets_api_key_env_from_config():
    resolver = CredentialResolver({"p": {"api_key_env": "TEST_KEY"}}, env_files=[])
    os.environ["TEST_KEY"] = "secret"
    try:
        result = resolver.validate("p")
        assert result.authenticated is True
        assert result.credential_valid is True
    finally:
        del os.environ["TEST_KEY"]


def test_all_providers_configured_skips_defaults():
    resolver = CredentialResolver({
        "defaults": {"default_provider": "x"},
        "p1": {"api_key_env": "P1_KEY"},
    }, env_files=[])
    results = resolver.all_providers_configured()
    assert "p1" in results
    assert "defaults" not in results
    assert results["p1"].authenticated is False


def test_load_env_files_skips_when_dotenv_unavailable(monkeypatch):
    monkeypatch.delenv("TEST_AUTH_KEY", raising=False)
    resolver = CredentialResolver({"p": {"api_key_env": "TEST_AUTH_KEY"}}, env_files=[])
    result = resolver.resolve("p")
    assert result == ""


def test_load_env_files_loads_existing_dotenv():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("DOTENV_TEST_KEY=dotenv_value\n")
        resolver = CredentialResolver({"p": {"api_key_env": "DOTENV_TEST_KEY"}}, env_files=[str(env_file)])
        result = resolver.resolve("p")
        assert result == "dotenv_value"
