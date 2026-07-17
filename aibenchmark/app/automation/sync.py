from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import SyncRecord
from aibenchmark.app.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class ModelSyncService:
    def __init__(self, manager: AutomationManager | None = None, registry: ProviderRegistry | None = None) -> None:
        self.manager = manager or AutomationManager()
        self.registry = registry or ProviderRegistry()

    def sync_provider(self, provider_name: str) -> SyncRecord:
        sync = self.manager.record_sync(
            SyncRecord(
                provider_name=provider_name,
                started_at=datetime.now(timezone.utc).isoformat(),
                status="running",
            )
        )
        try:
            models = self.registry.list_models(provider_name)
            sync = SyncRecord(
                sync_id=sync.sync_id,
                provider_name=provider_name,
                started_at=sync.started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                status="success",
                models_added=len(models),
            )
            self.manager.record_sync(sync)
            return self.manager.record_sync(sync)
        except Exception as exc:
            logger.error("Model sync failed for %s: %s", provider_name, exc)
            sync = SyncRecord(
                sync_id=sync.sync_id,
                provider_name=provider_name,
                started_at=sync.started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                status="failed",
                error=str(exc),
            )
            return self.manager.record_sync(sync)

    def sync_all(self) -> list[SyncRecord]:
        results = []
        for name in self.registry.list_providers():
            results.append(self.sync_provider(name))
        return results

