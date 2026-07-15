# Security

This document describes the security controls built into AI-Benchmark and the
expected hardening posture for downstream deployments.

## Principles

1. **Defense in depth**: validate inputs at the boundary, not only in business logic.
2. **Least privilege**: tools and services run with only the permissions they require.
3. **Fail closed**: ambiguous inputs are rejected rather than interpreted loosely.

## Input Validation

All external inputs are validated through `aibenchmark.app.validation`.
Use the typed validators instead of manual `if` checks so that validation stays
consistent across the CLI and library surface.

- `validate_provider_name` — checks that the value is a configured provider.
- `validate_model_name` — checks for non-empty strings and rejects injection characters.
- `validate_benchmark_name` — checks that the value is a known benchmark identifier.
- `validate_numeric_range` — bounds-checks numeric CLI inputs (temperature, token limits).
- `validate_positive_int` — guards resource counts and concurrency limits.
- `validate_path_safety` — ensures paths do not escape a base directory.

### JSON Schema Validation for CLI Inputs

`validate_json_schema` is a minimal JSON Schema draft-7 validator. It is intended
for configuration and command payloads where `jsonschema` would be too heavy. It
currently supports:

- `type`, `enum`, `required`, `properties`, `additionalProperties`
- String constraints: `minLength`, `maxLength`
- Number constraints: `minimum`, `maximum`
- Arrays: `items`

The validator refuses schemas that reference `$ref`, `anyOf`, `allOf`, `oneOf`, or
conditional keywords to keep the implementation auditable.

## YAML Safety

Always load external YAML through `safe_yaml_load`, which uses `yaml.safe_load`.
This prevents arbitrary object instantiation.

```python
from aibenchmark.app.validation import safe_yaml_load, YAMLSafetyError

try:
    config = safe_yaml_load(raw_yaml, label="benchmark config")
except YAMLSafetyError as exc:
    raise click.ClickException(str(exc))
```

## Dependency Management

Run `scripts/dependency_audit.py` to enumerate installed packages and check
them against known vulnerabilities. The script will use `safety` if installed;
otherwise it prints the static package list for manual review.

```bash
python scripts/dependency_audit.py audit-report.json
```

### CI expectations

- Pin dependencies in `pyproject.toml`.
- Run `dependency_audit.py` in CI before releases.
- Rotate API keys regularly; never hard-code keys in config files.

## Reporting Issues

Security issues should be reported to the maintainers rather than opened as
public issues.
