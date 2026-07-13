from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from aibenchmark.app.models import AuthResult

logger = logging.getLogger(__name__)


class CredentialResolver:
    def __init__(self, providers_config: dict[str, Any], env_files: list[str] | None = None) -> None:
        self.providers_config = providers_config
        self.env_files = env_files or [".env"]
        self._loaded = False

    def _load_env_files(self) -> None:
        if self._loaded:
            return
        dotenv_available = True
        try:
            from dotenv import load_dotenv
        except ImportError:
            dotenv_available = False
            logger.debug("python-dotenv not available; skipping .env files")

        for env_file in self.env_files:
            path = Path(env_file)
            if path.exists() and dotenv_available:
                load_dotenv(dotenv_path=path, override=False)

    def resolve(self, provider_name: str) -> str:
        self._load_env_files()
        cfg = self.providers_config.get(provider_name, {})
        if not isinstance(cfg, dict):
            return ""
        api_key_env = cfg.get("api_key_env", "API_KEY")
        return os.environ.get(api_key_env, "").strip()

    def validate(self, provider_name: str) -> AuthResult:
        self._load_env_files()
        cfg = self.providers_config.get(provider_name, {})
        if not isinstance(cfg, dict):
            return AuthResult(
                authenticated=False,
                provider=provider_name,
                message=f"Provider '{provider_name}' not configured.",
                credential_valid=False,
                validation_errors=["Missing configuration"],
            )
        api_key_env = cfg.get("api_key_env", "API_KEY")
        api_key = os.environ.get(api_key_env, "").strip()
        if not api_key:
            return AuthResult(
                authenticated=False,
                provider=provider_name,
                message=f"Missing API key: set {api_key_env}.",
                credential_valid=False,
                validation_errors=[f"Environment variable {api_key_env} is empty or missing"],
            )
        return AuthResult(
            authenticated=True,
            provider=provider_name,
            message="Credentials validated.",
            credential_valid=True,
            scopes=[],
        )

    def all_providers_configured(self) -> dict[str, AuthResult]:
        results: dict[str, AuthResult] = {}
        for name, cfg in self.providers_config.items():
            if name == "defaults" or not isinstance(cfg, dict):
                continue
            results[name] = self.validate(name)
        return results
