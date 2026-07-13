from __future__ import annotations

import logging
from typing import Sequence

from aibenchmark.app.models import BenchmarkResult, ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)


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
