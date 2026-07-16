from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Sequence

import yaml

from aibenchmark.app.models import BenchmarkResult, ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)

# Whitelist of provider names
_VALID_PROVIDERS = {
    "nvidia", "openrouter", "ollama", "huggingface", "gemini", "openai", "anthropic",
}


def validate_results(results: Sequence[BenchmarkResult]) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not results:
        issues.append(ValidationIssue("critical", "results", "Empty benchmark results"))
        return ValidationReport(valid=False, issues=issues)

    for result in results:
        if not result.scores:
            issues.append(ValidationIssue("major", "scoring", f"{result.provider.value}:{result.model} has no category scores"))
        if not result.model:
            issues.append(ValidationIssue("major", "results", f"Missing model name for result: {result.provider.value}"))

    weight_sum = sum(s.weight for r in results for s in r.scores)
    if weight_sum <= 0:
        issues.append(ValidationIssue("critical", "weights", "Sum of weights is zero or negative"))

    overalls = [r.overall for r in results]
    if len(set(round(v, 4) for v in overalls)) < 2 and len(overalls) > 1:
        issues.append(ValidationIssue("major", "discrimination", "Benchmark does not distinguish between models"))

    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_metadata(result: BenchmarkResult) -> ValidationReport:
    issues: list[ValidationIssue] = []
    required = [
        ("provider", result.provider),
        ("model", result.model),
        ("timestamp", result.metadata.get("timestamp")),
    ]
    for name, value in required:
        if not value:
            issues.append(ValidationIssue("critical", "metadata", f"Missing required field: {name}"))
    if result.scores and not result.overall:
        issues.append(ValidationIssue("major", "scoring", "Overall score not calculated"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_provider_name(name: str) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if not isinstance(name, str) or not name:
        issues.append(ValidationIssue("critical", "provider", "Provider name must be a non-empty string"))
    elif name not in _VALID_PROVIDERS:
        issues.append(ValidationIssue("critical", "provider", f"Unrecognized provider: {name}"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_model_name(name: str) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if not isinstance(name, str) or not name:
        issues.append(ValidationIssue("critical", "model", "Model name must be a non-empty string"))
    elif not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.\-/]*$", name):
        issues.append(ValidationIssue("critical", "model", f"Model name has suspicious characters: {name}"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_benchmark_name(name: str) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if not isinstance(name, str) or not name:
        issues.append(ValidationIssue("critical", "benchmark", "Benchmark name must be a non-empty string"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_numeric_range(value: Any, min_v: float | None = None, max_v: float | None = None) -> ValidationReport:
    issues: list[ValidationIssue] = []
    try:
        fv = float(value)
    except (TypeError, ValueError):
        issues.append(ValidationIssue("critical", "numeric", f"Value is not numeric: {value}"))
        return ValidationReport(valid=False, issues=issues)
    if min_v is not None and fv < min_v:
        issues.append(ValidationIssue("critical", "numeric", f"Value {fv} is below minimum {min_v}"))
    if max_v is not None and fv > max_v:
        issues.append(ValidationIssue("critical", "numeric", f"Value {fv} is above maximum {max_v}"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_path_safety(path: str | Path, base_dir: Path) -> ValidationReport:
    issues: list[ValidationIssue] = []
    p = Path(path)
    if not str(path):
        issues.append(ValidationIssue("critical", "path", "Path is empty"))
        return ValidationReport(valid=False, issues=issues)
    try:
        resolved = p.resolve()
        base = base_dir.resolve()
        if not str(resolved).startswith(str(base)):
            issues.append(ValidationIssue("critical", "path", f"Path escapes base directory: {resolved}"))
    except Exception as exc:
        issues.append(ValidationIssue("critical", "path", f"Invalid path: {exc}"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


def validate_positive_int(value: Any) -> ValidationReport:
    issues: list[ValidationIssue] = []
    try:
        iv = int(value)
    except (TypeError, ValueError):
        issues.append(ValidationIssue("critical", "integer", "Value is not an integer"))
        return ValidationReport(valid=False, issues=issues)
    if iv <= 0:
        issues.append(ValidationIssue("critical", "integer", f"Value must be positive: {iv}"))
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


# --- YAML safe load wrapper ---


class YAMLSafetyError(Exception):
    """Raised when unsafe YAML constructs are detected."""


def safe_yaml_load(text: str | bytes, label: str = "") -> Any:
    """Load YAML using the safe loader. Reject Python-specific tags."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise YAMLSafetyError(f"YAML parse error in {label}: {exc}") from exc
    # Reject python-specific tags that might sneak through
    return data


# --- JSON schema validation ---


class JSONSchemaValidationError(Exception):
    """Raised when JSON schema validation fails."""


def validate_json_schema(data: Any, schema: dict[str, Any], label: str = "input") -> ValidationReport:
    """Minimal JSON Schema draft-7 validator for CLI inputs.

    Supports type, enum, required, properties, additionalProperties, minimum/maximum,
    and minLength/maxLength. Raises JSONSchemaValidationError for unsupported schema features.
    """
    issues: list[ValidationIssue] = []

    def _check(node: Any, definition: dict[str, Any], path: str) -> None:
        if not isinstance(definition, dict):
            # Any value is valid when schema is not a dict
            return
        schema_type = definition.get("type")
        if schema_type == "object":
            if not isinstance(node, dict):
                issues.append(ValidationIssue("critical", "schema", f"{path or 'root'}: expected object, got {type(node).__name__}"))
                return
            required = definition.get("required", [])
            for key in required:
                if key not in node:
                    issues.append(ValidationIssue("critical", "schema", f"{path}.{key}: required field missing"))
            props = definition.get("properties", {})
            for key, value in node.items():
                if key in props:
                    _check(value, props[key], f"{path}.{key}")
            additional = definition.get("additionalProperties")
            if additional is False:
                for key in node.keys():
                    if key not in props:
                        issues.append(ValidationIssue("critical", "schema", f"{path}.{key}: additional property not allowed"))
            return
        if schema_type == "array":
            if not isinstance(node, list):
                issues.append(ValidationIssue("critical", "schema", f"{path}: expected array, got {type(node).__name__}"))
                return
            items = definition.get("items")
            if items:
                for idx, item in enumerate(node):
                    _check(item, items, f"{path}[{idx}]")
            return
        if schema_type == "string":
            if not isinstance(node, str):
                issues.append(ValidationIssue("critical", "schema", f"{path}: expected string, got {type(node).__name__}"))
                return
            if "minLength" in definition and len(node) < int(definition["minLength"]):
                issues.append(ValidationIssue("critical", "schema", f"{path}: string shorter than minLength"))
            if "maxLength" in definition and len(node) > int(definition["maxLength"]):
                issues.append(ValidationIssue("critical", "schema", f"{path}: string longer than maxLength"))
            if "enum" in definition and node not in definition["enum"]:
                issues.append(ValidationIssue("critical", "schema", f"{path}: value not in allowed enum"))
            return
        if schema_type in {"integer", "number"}:
            if isinstance(schema_type, str) and schema_type == "integer" and not isinstance(node, int):
                issues.append(ValidationIssue("critical", "schema", f"{path}: expected integer"))
                return
            if not isinstance(node, (int, float)):
                issues.append(ValidationIssue("critical", "schema", f"{path}: expected number, got {type(node).__name__}"))
                return
            if "minimum" in definition and node < definition["minimum"]:
                issues.append(ValidationIssue("critical", "schema", f"{path}: below minimum"))
            if "maximum" in definition and node > definition["maximum"]:
                issues.append(ValidationIssue("critical", "schema", f"{path}: above maximum"))
            return
        if schema_type == "boolean":
            if not isinstance(node, bool):
                issues.append(ValidationIssue("critical", "schema", f"{path}: expected boolean"))
            return
        # 'anyOf' / 'allOf' / 'oneOf' could be added here; omit to keep implementation minimal
        if "enum" in definition and node not in definition["enum"]:
            issues.append(ValidationIssue("critical", "schema", f"{path}: value not in allowed enum"))

    # Detect unsupported features up-front
    unsupported = {"anyOf", "allOf", "oneOf", "not", "if", "then", "else", "$ref", "allOf", "definitions"}
    if set(schema.keys()) & unsupported:
        raise JSONSchemaValidationError(f"Unsupported JSON Schema features in {label}")

    _check(data, schema, "")
    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)


__all__ = [
    "validate_results",
    "validate_metadata",
    "validate_provider_name",
    "validate_model_name",
    "validate_benchmark_name",
    "validate_numeric_range",
    "validate_path_safety",
    "validate_positive_int",
    "validate_json_schema",
    "YAMLSafetyError",
    "safe_yaml_load",
    "JSONSchemaValidationError",
    "ValidationReport",
    "ValidationIssue",
]
