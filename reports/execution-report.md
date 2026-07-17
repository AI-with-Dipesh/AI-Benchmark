# AI-Benchmark Execution Report (Sprint 11.5 Fixed)
**Generated**: 2026-07-17 06:00:53 UTC
**Platform**: AI-Benchmark v1.3.0
**Models with complete data**: 3

---

## Model Rankings (Corrected Overall)

| Rank | Model | Corrected Overall | Coding | Debugging | Reasoning | Research | Code Review | JSON | Instruction | General | Latency |
|------|-------|-------------------|--------|-----------|-----------|----------|-------------|------|-------------|---------|---------|
| 1 | tencent/hy3:free | 0.5240 | 0.750 | 0.120 | 0.674 | 0.863 | 0.642 | 0.000 | 0.039 | 0.121 | 0.623 |
| 2 | openrouter/free | 0.0582 | 0.600 | 0.120 | 0.737 | 0.633 | 0.381 | 0.000 | 0.039 | 0.365 | 0.640 |
| 3 | cohere/north-mini-code:free | 0.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Notes

- Corrected Overall uses raw scores for non-latency categories; latency uses stored normalized score.
- The `runs.overall` field previously stored 0.0 due to a normalization bug; now fixed in engine.py.
- Weights: coding 25, debugging 20, reasoning 15, research 15, code_review 10, latency 10, json 5, instruction 5, general 5.
- Only completed runs with 9 benchmark categories are included.