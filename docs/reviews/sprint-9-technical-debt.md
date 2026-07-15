# Sprint 9 Technical Debt Register

## Active Technical Debt Items

| ID | Description | Priority | Origin Sprint | Recommended Sprint | Risk | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TD-Coverage-7 | Overall test coverage remains below the 95% long-term target due to uncovered legacy Sprint 1–3 modules. | High | Sprint 7 | Sprint 9 | Low | TBD | Accepted |
| TD-ResourceWarnings-9 | Test suite may emit `ResourceWarning` from PyYAML C extension internals during YAML parsing in certain environments. | Low | Sprint 9 | Sprint 10+ | Low | TBD | Accepted workaround |

### TD-Coverage-7 Remediation Plan
- Sprint 9: Add targeted tests for uncovered legacy modules; target 93% coverage.
- Sprint 10+: Continue expanding legacy module tests until 95% reached.

### TD-ResourceWarnings-9 Evidence
- Executed test suite with `pytest -W error::ResourceWarning`; no ResourceWarnings emitted by project code.
- Root cause is constrained to PyYAML C extension behavior in specific environments.
- Safe suppression is configured via `pyproject.toml` pytest `filterwarnings = ["ignore::ResourceWarning"]`.
- Upstream monitoring recommended; remove suppression when PyYAML ships a fix.

## Deferred Technical Debt
None.

## Retired Technical Debt
None.
