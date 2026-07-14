from __future__ import annotations


import pytest

from aibenchmark.app.auth import CredentialResolver


class TestCredentialResolver:
    def test_resolve_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAKE_API_KEY", "secret123")
        providers = {"test_provider": {"api_key_env": "FAKE_API_KEY"}}
        resolver = CredentialResolver(providers)
        assert resolver.resolve("test_provider") == "secret123"

    def test_resolve_missing_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_API_KEY", raising=False)
        providers = {"test_provider": {"api_key_env": "MISSING_API_KEY"}}
        resolver = CredentialResolver(providers)
        assert resolver.resolve("test_provider") == ""

    def test_validate_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VALID_KEY", "tok123")
        providers = {"test_provider": {"api_key_env": "VALID_KEY"}}
        resolver = CredentialResolver(providers)
        result = resolver.validate("test_provider")
        assert result.authenticated is True
        assert result.credential_valid is True

    def test_validate_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_KEY", raising=False)
        providers = {"test_provider": {"api_key_env": "MISSING_KEY"}}
        resolver = CredentialResolver(providers)
        result = resolver.validate("test_provider")
        assert result.authenticated is False
        assert "MISSING_KEY" in result.message

    def test_all_providers_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("A1", "v1")
        monkeypatch.setenv("A2", "v2")
        providers = {
            "p1": {"api_key_env": "A1"},
            "p2": {"api_key_env": "A2"},
            "defaults": {},
        }
        resolver = CredentialResolver(providers)
        results = resolver.all_providers_configured()
        assert "p1" in results
        assert "p2" in results
        assert "defaults" not in results
        assert results["p1"].credential_valid is True
        assert results["p2"].credential_valid is True
