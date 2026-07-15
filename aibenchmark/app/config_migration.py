from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationResult:
    migrated: bool
    from_version: str
    to_version: str
    changes: list[str]
    migrated_data: dict[str, Any] | None = None


class ConfigMigrationError(Exception):
    """Raised when configuration migration fails."""


def migrate_0_7_to_1_0(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Migrate configuration from schema version 0.7 to 1.0."""
    changes: list[str] = []
    # Ensure schema_version is declared
    if data.get("schema_version") != "1.0":
        data["schema_version"] = "1.0"
        changes.append("Set schema_version=1.0")
    # Ensure benchmark_version defaults to 1.0.0 when absent
    if not data.get("benchmark_version"):
        data["benchmark_version"] = "1.0.0"
        changes.append("Set benchmark_version=1.0.0")
    return data, changes


MIGRATIONS = {
    ("0.7", "1.0"): migrate_0_7_to_1_0,
}


def apply_migration(data: dict[str, Any], from_version: str, to_version: str) -> MigrationResult:
    if from_version == to_version:
        return MigrationResult(False, from_version, to_version, [], migrated_data=None)
    key = (from_version, to_version)
    if key not in MIGRATIONS:
        raise ConfigMigrationError(
            f"No migration path from schema version {from_version} to {to_version}"
        )
    migrated_data, changes = MIGRATIONS[key](data.copy())
    return MigrationResult(True, from_version, to_version, changes, migrated_data=migrated_data)
