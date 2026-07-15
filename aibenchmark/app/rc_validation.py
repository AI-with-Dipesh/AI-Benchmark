from __future__ import annotations

import logging
from typing import Any

from aibenchmark.app.models import BenchmarkResult, ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)


class RCValidationError(Exception):
    """Raised when a boundary check defined in AD-73 fails."""


def check_overall_bounds(result: BenchmarkResult) -> ValidationReport:
    issues: list[ValidationIssue] = []
    # Overall must be within [0.0, 1.0]
    if not (0.0 <= result.overall <= 1.0):
        issues.append(ValidationIssue(
            severity="critical",
            category="bounds",
            message=f"overall score {result.overall} is outside [0.0, 1.0]",
            detail="AD-73 overall boundary",
        ))
    return ValidationReport(valid=not issues, issues=issues)


def check_scores_bounds(result: BenchmarkResult) -> ValidationReport:
    issues: list[ValidationIssue] = []
    for score in result.scores:
        if not (0.0 <= score.raw <= 1.0):
            benchmark_name = score.benchmark.value if hasattr(score.benchmark, "value") else str(score.benchmark)
            issues.append(ValidationIssue(
                severity="major",
                category="bounds",
                message=f"raw score {score.raw} for {benchmark_name} is outside [0.0, 1.0]",
                detail="AD-73 raw score boundary",
            ))
        if not (0.0 <= score.normalized <= 1.0):
            benchmark_name = score.benchmark.value if hasattr(score.benchmark, "value") else str(score.benchmark)
            issues.append(ValidationIssue(
                severity="major",
                category="bounds",
                message=f"normalized score {score.normalized} for {benchmark_name} is outside [0.0, 1.0]",
                detail="AD-73 normalized boundary",
            ))
        if score.weight <= 0:
            benchmark_name = score.benchmark.value if hasattr(score.benchmark, "value") else str(score.benchmark)
            issues.append(ValidationIssue(
                severity="major",
                category="bounds",
                message=f"weight {score.weight} for {benchmark_name} must be positive",
                detail="AD-73 weight boundary",
            ))
    return ValidationReport(valid=not issues, issues=issues)


def check_metadata_bounds(result: BenchmarkResult) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if result.retry_count < 0:
        issues.append(ValidationIssue(
            severity="minor",
            category="bounds",
            message=f"retry_count {result.retry_count} must be >= 0",
            detail="AD-73 retry_count boundary",
        ))
    if result.estimated_cost is not None and result.estimated_cost < 0:
        issues.append(ValidationIssue(
            severity="minor",
            category="bounds",
            message=f"estimated_cost {result.estimated_cost} must be >= 0",
            detail="AD-73 estimated_cost boundary",
        ))
    if result.temperature is not None and not (0.0 <= result.temperature <= 2.0):
        issues.append(ValidationIssue(
            severity="minor",
            category="bounds",
            message=f"temperature {result.temperature} outside typical [0.0, 2.0]",
            detail="AD-73 temperature boundary",
        ))
    if result.top_p is not None and not (0.0 <= result.top_p <= 1.0):
        issues.append(ValidationIssue(
            severity="minor",
            category="bounds",
            message=f"top_p {result.top_p} outside [0.0, 1.0]",
            detail="AD-73 top_p boundary",
        ))
    return ValidationReport(valid=not issues, issues=issues)


def validate_rc_bounds(result: BenchmarkResult) -> ValidationReport:
    all_issues: list[ValidationIssue] = []
    for check in (check_overall_bounds, check_scores_bounds, check_metadata_bounds):
        report = check(result)
        all_issues.extend(report.issues)
    return ValidationReport(valid=not any(i.severity == "critical" for i in all_issues), issues=all_issues)
