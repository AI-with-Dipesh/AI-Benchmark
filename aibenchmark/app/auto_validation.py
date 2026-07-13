from __future__ import annotations

import logging
from typing import Sequence

from aibenchmark.app.models import BenchmarkResult, ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)


def auto_validate(results: Sequence[BenchmarkResult], runs: Sequence[Sequence[BenchmarkResult]] | None = None) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not results:
        issues.append(ValidationIssue("critical", "results", "Empty benchmark results"))
        return ValidationReport(valid=False, issues=issues)

    for result in results:
        if not result.scores:
            issues.append(ValidationIssue("critical", "scoring", f"{result.model}: has no benchmark scores"))
        if not result.model:
            issues.append(ValidationIssue("major", "results", f"Missing model name for result: {result.provider.value}"))
        if not result.provider:
            issues.append(ValidationIssue("critical", "metadata", f"Missing provider for result: {result.model}"))
        if result.metadata.get("timestamp") is None:
            issues.append(ValidationIssue("critical", "metadata", f"Missing timestamp for result: {result.model}"))
        if result.prompt_tokens is None:
            issues.append(ValidationIssue("minor", "metadata", f"{result.model}: prompt_tokens missing"))
        if result.completion_tokens is None:
            issues.append(ValidationIssue("minor", "metadata", f"{result.model}: completion_tokens missing"))
        if result.total_tokens is None and (result.prompt_tokens is None or result.completion_tokens is None):
            issues.append(ValidationIssue("minor", "metadata", f"{result.model}: total_tokens missing"))
        if result.estimated_cost is None:
            issues.append(ValidationIssue("minor", "cost", f"{result.model}: estimated_cost missing"))
        if result.timeout_status not in (None, "request", "benchmark", "category"):
            issues.append(ValidationIssue("major", "timeout", f"{result.model}: invalid timeout_status '{result.timeout_status}'"))
        if not result.model_version:
            issues.append(ValidationIssue("minor", "reproducibility", f"{result.model}: missing model_version"))
        if not result.benchmark_version:
            issues.append(ValidationIssue("minor", "reproducibility", f"{result.model}: missing benchmark_version"))
        if result.scores and not result.evaluation:
            issues.append(ValidationIssue("minor", "evaluation", f"{result.model}: missing evaluation label"))
        if result.scores and result.objective_validation is None:
            issues.append(ValidationIssue("minor", "validation", f"{result.model}: objective validation missing"))
        if result.scores and result.confidence is None:
            issues.append(ValidationIssue("minor", "confidence", f"{result.model}: confidence missing"))

    weight_sum = sum(s.weight for r in results for s in r.scores)
    if weight_sum <= 0:
        issues.append(ValidationIssue("critical", "weights", "Sum of weights is zero or negative"))

    overalls = [r.overall for r in results]
    if len(set(round(v, 4) for v in overalls)) < 2 and len(overalls) > 1:
        issues.append(ValidationIssue("major", "discrimination", "Benchmark does not distinguish between models"))

    for result in results:
        if result.scores and not result.overall:
            issues.append(ValidationIssue("major", "scoring", "Overall score not calculated"))

    if runs:
        from aibenchmark.app.statistics import outlier_runs, score_drift
        drift = score_drift(runs)
        unstable = [m for m, v in drift.items() if abs(v) > 0.1]
        for m in unstable:
            issues.append(ValidationIssue("major", "drift", f"Model {m} shows score drift > 0.1"))

        outliers = outlier_runs(runs)
        for idx, val in outliers:
            issues.append(ValidationIssue("major", "outlier", f"Run #{idx} is an outlier with overall {val:.2f}"))

    return ValidationReport(valid=not any(i.severity == "critical" for i in issues), issues=issues)
