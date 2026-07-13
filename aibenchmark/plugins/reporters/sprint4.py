from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.calibration import calibrate
from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.reliability import build_reliability
from aibenchmark.app.statistics import outlier_runs, score_drift, summarize
from aibenchmark.app.token_accounting import cost_report, token_report
from aibenchmark.app.auto_validation import auto_validate


def _resolve_runs(results: list[BenchmarkResult], kwargs: dict[str, Any]) -> list[list[BenchmarkResult]]:
    runs = kwargs.get("runs")
    if isinstance(runs, list) and runs and isinstance(runs[0], list):
        return runs
    return [results]


def generate_validation(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = kwargs.get("runs")
    if not isinstance(runs, list):
        runs = None
    report = auto_validate(results, runs=runs)
    lines = ["# Validation Report\n", report.summary()]
    path.write_text("\n".join(lines) + "\n")


def generate_calibration(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = _resolve_runs(results, kwargs)
    report = calibrate(runs)
    lines = ["# Calibration Report\n", f"Inflation factor: {report.inflation_factor}", "Category bias:"]
    for cat, bias in report.category_bias.items():
        lines.append(f"- {cat}: {bias:+.4f}")
    lines.append("Discriminative power:")
    for cat, power in report.discriminative_power.items():
        lines.append(f"- {cat}: {power:.4f}")
    lines.append(f"Recommendation instability: {report.recommendation_instability:.4f}")
    for issue in report.issues:
        lines.append(f"- [{issue.severity}] {issue.category}: {issue.message}")
    path.write_text("\n".join(lines) + "\n")


def generate_reliability(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = _resolve_runs(results, kwargs)
    report = build_reliability(runs)
    lines = ["# Reliability Report\n", "| Provider:Model | Success | Failure | Timeout | Retry | Avg Latency (ms) | P95 |", "|---|---|---|---|---|---|---|"]
    for key, entry in report.entries.items():
        avg = f"{entry.average_latency_ms:.1f}" if entry.average_latency_ms is not None else "-"
        p95 = f"{entry.p95_latency_ms:.1f}" if entry.p95_latency_ms is not None else "-"
        lines.append(f"| {key} | {entry.success_count} | {entry.failure_count} | {entry.timeout_count} | {entry.retry_count} | {avg} | {p95} |")
    lines.append("\nProvider availability:")
    for provider, avail in report.provider_availability.items():
        lines.append(f"- {provider}: {avail:.2f}")
    path.write_text("\n".join(lines) + "\n")


def generate_tokens(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = _resolve_runs(results, kwargs)
    flat = [r for run in runs for r in run]
    report = token_report(flat)
    lines = ["# Token Usage Report\n", f"Prompt tokens: {report.prompt_tokens}", f"Completion tokens: {report.completion_tokens}", f"Total tokens: {report.total_tokens}", f"Estimated cost: {report.estimated_cost:.4f}"]
    if report.tokens_per_second is not None:
        lines.append(f"Tokens per second: {report.tokens_per_second:.2f}")
    lines.append("\nBreakdown by model:")
    for key, usage in report.provider_model_breakdown.items():
        lines.append(f"- {key}: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}")
    path.write_text("\n".join(lines) + "\n")


def generate_cost(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = _resolve_runs(results, kwargs)
    report = cost_report(runs, price_lookup=kwargs.get("price_lookup"))
    lines = ["# Cost Report\n", f"Total cost: {report.total_cost:.4f}"]
    lines.append("\nBy provider:")
    for provider, cost in report.by_provider.items():
        lines.append(f"- {provider}: {cost:.4f}")
    lines.append("\nBy model:")
    for model, cost in report.by_model.items():
        lines.append(f"- {model}: {cost:.4f}")
    path.write_text("\n".join(lines) + "\n")


def generate_metadata(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    lines = ["# Benchmark Metadata\n", "| Model | Provider | Benchmark Version | Prompt Version | Temperature | Top P | Seed | Prompt Tokens | Completion Tokens | Total Tokens | Estimated Cost | Retry Count | Timeout Status |"]
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        rows = [
            r.model,
            r.provider.value,
            r.benchmark_version or "-",
            r.prompt_version or "-",
            r.temperature if r.temperature is not None else "-",
            r.top_p if r.top_p is not None else "-",
            r.seed if r.seed is not None else "-",
            r.prompt_tokens or 0,
            r.completion_tokens or 0,
            r.total_tokens or 0,
            f"{r.estimated_cost:.4f}" if r.estimated_cost is not None else "-",
            r.retry_count,
            r.timeout_status or "-",
        ]
        lines.append("| " + " | ".join(str(x) for x in rows) + " |")
    path.write_text("\n".join(lines) + "\n")


def _generate_governance(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    lines = ["# Governance Report\n"]
    if not results:
        path.write_text("\n".join(lines) + "No results.\\n")
        return
    best = max(results, key=lambda r: r.overall)
    lines.append(f"Recommended model: {best.model} ({best.provider.value}) overall={best.overall:.2f}\n")
    lines.append("Key factors:")
    for s in best.scores:
        lines.append(f"- {s.benchmark.value}: normalized={s.normalized:.2f} weight={s.weight:.2f}")
    lines.append("\nAlternatives considered:")
    for r in results:
        if r.model != best.model:
            lines.append(f"- {r.model} ({r.provider.value}) overall={r.overall:.2f}")
            for s in r.scores:
                if s.normalized >= best.scores[0].normalized - 0.05:
                    lines.append(f"  - {s.benchmark.value}: competitive at {s.normalized:.2f}")
    lines.append("\nConfidence derivation:")
    lines.append(f"- Primary score: {best.scores[0].normalized:.2f}")
    lines.append(f"- Confidence: {best.confidence:.2f}" if best.confidence is not None else "- Confidence: n/a")
    lines.append(f"- Evaluation: {best.evaluation}" if best.evaluation else "- Evaluation: n/a")
    lines.append(f"- Objective validation: {best.objective_validation}" if best.objective_validation is not None else "- Objective validation: n/a")
    lines.append("\nBias / calibration notes:")
    try:
        cal = calibrate([results])
        if cal.issues:
            for issue in cal.issues:
                lines.append(f"- [{issue.severity}] {issue.category}: {issue.message}")
        else:
            lines.append("- No calibration issues detected.")
    except Exception as exc:
        lines.append(f"- Calibration skipped: {exc}")
    path.write_text("\n".join(lines) + "\n")


def generate_statistics(run: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    runs = _resolve_runs(run, kwargs)
    lines = ["# Statistical Summary\n"]
    if not runs or not any(runs):
        path.write_text("\n".join(lines) + "No data.\n")
        return

    # Per-run stats
    for idx, results in enumerate(runs, start=1):
        lines.append(f"## Run {idx}\n")
        if not results:
            lines.append("No results.\n")
            continue
        category_values: dict[str, list[float]] = {}
        for r in results:
            for s in r.scores:
                category_values.setdefault(s.benchmark.value, []).append(s.normalized)
        for name, vals in sorted(category_values.items()):
            stats = summarize(vals)
            lines.append(f"### {name}\n")
            lines.append(f"- Mean: {stats.mean:.4f}")
            lines.append(f"- Median: {stats.median:.4f}")
            lines.append(f"- Std Dev: {stats.std_dev:.4f}")
            lines.append(f"- CV: {stats.coefficient_of_variation:.4f}")
            lines.append(f"- 95% CI: {stats.confidence_interval_95[0]:.4f} - {stats.confidence_interval_95[1]:.4f}")
            lines.append("")

    # Cross-run metrics when available
    if len(runs) > 1:
        flat = [r for run in runs for r in run]
        lines.append("## Cross-Run Metrics\n")
        drift = score_drift(runs)
        for model, val in drift.items():
            lines.append(f"- {model} score drift: {val:+.4f}")
        outliers = outlier_runs(runs)
        for idx, val in outliers:
            lines.append(f"- Run #{idx} outlier overall: {val:.4f}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


@register(PluginCategory.REPORTER, "validation")
class ValidationReporter:
    plugin_name = "validation"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_validation(results, path, **kwargs)


@register(PluginCategory.REPORTER, "calibration")
class CalibrationReporter:
    plugin_name = "calibration"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_calibration(results, path, **kwargs)


@register(PluginCategory.REPORTER, "reliability")
class ReliabilityReporter:
    plugin_name = "reliability"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_reliability(results, path, **kwargs)


@register(PluginCategory.REPORTER, "statistics")
class StatisticsReporter:
    plugin_name = "statistics"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_statistics(results, path, **kwargs)


@register(PluginCategory.REPORTER, "tokens")
class TokensReporter:
    plugin_name = "tokens"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_tokens(results, path, **kwargs)


@register(PluginCategory.REPORTER, "cost")
class CostReporter:
    plugin_name = "cost"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_cost(results, path, **kwargs)


@register(PluginCategory.REPORTER, "metadata")
class MetadataReporter:
    plugin_name = "metadata"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_metadata(results, path)


@register(PluginCategory.REPORTER, "governance")
class GovernanceReporter:
    plugin_name = "governance"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        _generate_governance(results, path)
