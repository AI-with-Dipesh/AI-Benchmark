from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 3600  # 1 hour
_DEFAULT_PATH = Path.home() / ".aibenchmark" / "model_cache.json"


class ModelCache:
    """File-backed cache for provider model lists with TTL expiration.

    Cache entries are stored as a JSON mapping of provider_name ->
    {"models": [...], "fetched_at": epoch_seconds}.
    """

    def __init__(self, path: Path | None = None, ttl: int = _DEFAULT_TTL) -> None:
        self.path = path or _DEFAULT_PATH
        self.ttl = int(ttl)

    def get(self, provider_name: str) -> list[str] | None:
        data = self._read()
        entry = data.get(provider_name)
        if not entry:
            return None
        fetched_at = float(entry.get("fetched_at", 0))
        if (time.time() - fetched_at) > self.ttl:
            # Expired: remove and return None to trigger refresh
            data.pop(provider_name, None)
            self._write(data)
            return None
        models = entry.get("models", [])
        if isinstance(models, list):
            return [str(m) for m in models]
        return None

    def set(self, provider_name: str, models: list[str]) -> None:
        data = self._read()
        data[provider_name] = {
            "models": [str(m) for m in models],
            "fetched_at": time.time(),
        }
        self._write(data)

    def invalidate(self, provider_name: str | None = None) -> None:
        data = self._read()
        if provider_name:
            data.pop(provider_name, None)
        else:
            data.clear()
        self._write(data)

    def stats(self) -> dict[str, Any]:
        data = self._read()
        total = 0
        expired = 0
        now = time.time()
        for entry in data.values():
            if isinstance(entry, dict) and "models" in entry:
                total += 1
                if (now - float(entry.get("fetched_at", 0))) > self.ttl:
                    expired += 1
        return {"cached_providers": total, "expired_entries": expired, "path": str(self.path)}

    def _read(self) -> dict[str, Any]:
        try:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception as exc:
            logger.debug("Model cache read failed: %s", exc)
        return {}

    def _write(self, data: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self.path)
        except Exception as exc:
            logger.debug("Model cache write failed: %s", exc)
