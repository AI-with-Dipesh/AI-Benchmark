# BENCHMARK VALIDATION REPORT — Sprint 11.5

**Generated**: 2026-07-17 06:00:11 UTC
**Platform**: AI-Benchmark v1.3.0

---

## Validation Scope

Validated all benchmark calculation paths after engine scoring fixes.

### Subsystems Validated

| Subsystem | Status |
|-----------|--------|
| Score normalization (`_normalize`) | VERIFIED — correct clamp [0,1] |
| Weighted score calculation (`Score.__post_init__`) | VERIFIED — weighted = normalized * weight |
| Overall aggregation (`BenchmarkResult.calculate_overall`) | VERIFIED — sum(weighted)/sum(weights) |
| Engine score preservation (fix applied) | VERIFIED — uses plugin-computed Score |
| Historical DB storage (`save_run`) | VERIFIED — stores raw/normalized/weighted correctly |
| Historical DB load (`load_run`) | VERIFIED — reconstructs Score from DB columns |
| Aggregate run overall (`save_run`) | VERIFIED — weighted avg across all categories |
| Reproducibility | VERIFIED — deterministic prompts, fixed params |
| Validator (`validate_metadata`) | VERIFIED — zero overall no longer false-positive |
| Leaderboard/analytics consumers | VERIFIED — read from Score/overall correctly |

### Validation Methods

1. Unit tests: 500 tests pass (including 4 new regression tests)
2. Integration test: Ran `openrouter -m tencent/hy3:free -b coding` → `coding: 0.75` (previously 0.00)
3. Cross-check: Computed aggregate overall independently from benchmark_scores table and compared to runs.overall
4. Regression tests: Added for both fixed bugs

### Stored Data Verification

Verified that for run_id 29 (tencent/hy3:free):

| Category | Raw | Normalized | Weight | Weighted |
|----------|-----|------------|--------|----------|
| coding | 0.750 | 0.750 | 25 | 18.750 |
| debugging | 0.120 | 0.120 | 20 | 2.400 |
| general | 0.121 | 0.121 | 5 | 0.607 |
| instruction | 0.039 | 0.039 | 5 | 0.194 |
| json | 0.000 | 0.000 | 5 | 0.000 |
| latency | 1887.0ms | 0.623 | 10 | 6.226 |
| reasoning | 0.674 | 0.674 | 15 | 10.106 |
| research | 0.863 | 0.863 | 15 | 12.938 |
| code_review | 0.642 | 0.642 | 10 | 6.416 |
| **Aggregate** | | | **110** | **57.637** |

**Corrected overall**: 57.637 / 110 = 0.5240

---

## Deviations

None. All values independently verified.
