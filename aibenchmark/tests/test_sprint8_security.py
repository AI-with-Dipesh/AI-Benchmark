"""Sprint 8 security hardening tests."""

from __future__ import annotations

import io

import pytest
import yaml

from aibenchmark.app.validation import (
    JSONSchemaValidationError,
    YAMLSafetyError,
    JSONSchemaValidationError,
    safe_yaml_load,
    validate_benchmark_name,
    validate_json_schema,
    validate_model_name,
    validate_numeric_range,
    validate_path_safety,
    validate_positive_int,
    validate_provider_name,
)


def test_validate_provider_name_known() -> None:
    report = validate_provider_name("ollama")
    assert report.valid is True


def test_validate_provider_name_unknown() -> None:
    report = validate_provider_name("evil-provider")
    assert report.valid is False
    assert any(issue.category == "provider" for issue in report.issues)


def test_validate_provider_name_empty() -> None:
    report = validate_provider_name("")
    assert report.valid is False


def test_validate_model_name_allowed_chars() -> None:
    report = validate_model_name("gpt-4-turbo")
    assert report.valid is True


def test_validate_model_name_suspicious_chars() -> None:
    report = validate_model_name("bad; rm -rf /")
    assert report.valid is False


def test_validate_benchmark_name_empty() -> None:
    report = validate_benchmark_name("")
    assert report.valid is False


def test_validate_numeric_range_in_range() -> None:
    report = validate_numeric_range(0.5, min_v=0.0, max_v=1.0)
    assert report.valid is True


def test_validate_numeric_range_below_min() -> None:
    report = validate_numeric_range(-1, min_v=0, max_v=1)
    assert report.valid is False


def test_validate_positive_int_valid() -> None:
    report = validate_positive_int(4)
    assert report.valid is True


def test_validate_positive_int_zero() -> None:
    report = validate_positive_int(0)
    assert report.valid is False


def test_validate_path_safety_escapes(tmp_path: Path) -> None:
    report = validate_path_safety("/etc/passwd", base_dir=tmp_path)
    assert report.valid is False


def test_validate_path_safety_within_base(tmp_path: Path) -> None:
    child = tmp_path / "reports" / "out.json"
    report = validate_path_safety(child, base_dir=tmp_path)
    assert report.valid is True


def test_safe_yaml_load_valid() -> None:
    text = "provider: ollama\nmodel: llama3"
    data = safe_yaml_load(text, label="config")
    assert data["provider"] == "ollama"


def test_safe_yaml_load_invalid_yaml() -> None:
    with pytest.raises(YAMLSafetyError):
        safe_yaml_load(": bad yaml ::", label="broken")


def test_safe_yaml_load_refuses_python_tags() -> None:
    text = "!!python/object/apply:os.system ['echo pwned']"
    with pytest.raises(YAMLSafetyError):
        safe_yaml_load(text, label="malicious")


def test_validate_json_schema_valid() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}, "workers": {"type": "integer", "minimum": 1}},
    }
    data = {"name": "bench", "workers": 4}
    report = validate_json_schema(data, schema, label="run_config")
    assert report.valid is True


def test_validate_json_schema_missing_required() -> None:
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    report = validate_json_schema({}, schema, label="run_config")
    assert report.valid is False


def test_validate_json_schema_additional_properties_disallowed() -> None:
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }
    report = validate_json_schema({"name": "x", "extra": 1}, schema, label="run_config")
    assert report.valid is False


def test_validate_json_schema_enum() -> None:
    schema = {"type": "string", "enum": ["json", "md", "csv"]}
    report = validate_json_schema("txt", schema, label="format")
    assert report.valid is False


def test_validate_json_schema_unsupported_feature_raises() -> None:
    with pytest.raises(JSONSchemaValidationError):
        validate_json_schema({"a": 1}, {"anyOf": [{}]}, label="schema")
