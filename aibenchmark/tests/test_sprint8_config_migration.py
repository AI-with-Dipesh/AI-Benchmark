from __future__ import annotations

import pytest

from aibenchmark.app.config_migration import (
    ConfigMigrationError,
    MIGRATIONS,
    MigrationResult,
    apply_migration,
    migrate_0_7_to_1_0,
)


def test_migrate_0_7_to_1_0_sets_schema_version():
    data = {"weights": {"coding": 25}}
    result = migrate_0_7_to_1_0(data)
    assert result[0]["schema_version"] == "1.0"
    assert "Set schema_version=1.0" in result[1]


def test_migrate_0_7_to_1_0_sets_benchmark_version_when_missing():
    data = {"weights": {"coding": 25}}
    result = migrate_0_7_to_1_0(data)
    assert result[0]["benchmark_version"] == "1.0.0"
    assert "Set benchmark_version=1.0.0" in result[1]


def test_migrate_0_7_to_1_0_preserves_existing_benchmark_version():
    data = {"weights": {"coding": 25}, "benchmark_version": "0.7.0"}
    result = migrate_0_7_to_1_0(data)
    assert result[0]["benchmark_version"] == "0.7.0"


def test_migrate_0_7_to_1_0_preserves_existing_schema_version():
    data = {"schema_version": "1.0", "weights": {"coding": 25}}
    result = migrate_0_7_to_1_0(data)
    assert result[0]["schema_version"] == "1.0"


def test_apply_migration_noop_when_same_version():
    data = {"schema_version": "1.0"}
    result = apply_migration(data, "1.0", "1.0")
    assert result.migrated is False
    assert result.from_version == "1.0"
    assert result.to_version == "1.0"
    assert result.changes == []


def test_apply_migration_runs_and_returns_changes():
    data = {"weights": {"coding": 25}}
    result = apply_migration(data, "0.7", "1.0")
    assert result.migrated is True
    assert result.from_version == "0.7"
    assert result.to_version == "1.0"
    assert len(result.changes) >= 1


def test_apply_migration_missing_path_raises():
    with pytest.raises(ConfigMigrationError, match="No migration path"):
        apply_migration({}, "1.0", "2.0")


def test_does_not_mutate_original_data():
    original = {"weights": {"coding": 25}}
    result = apply_migration(original, "0.7", "1.0")
    # apply_migration should not mutate the input dict
    assert "schema_version" not in original
    assert result.migrated_data["schema_version"] == "1.0"


def test_migrations_registry_has_expected_entries():
    assert ("0.7", "1.0") in MIGRATIONS
