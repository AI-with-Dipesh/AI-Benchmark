from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.analytics import (
    build_leaderboard,
    recommend,
    build_team,
    build_comparison,
    build_trends,
    best_value,
    most_stable,
    fastest,
    highest_quality,
)
from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.history import load_latest


def _load_results_from_runs(runs: int, db_path: Path | None = None) -> list[list[BenchmarkResult]]:
    latest = load_latest(runs, db_path=db_path)
    return latest if latest else []


def generate_leaderboard(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    rows = build_leaderboard(results)
    lines = [
        "# Leaderboard\n",
        "| Rank | Model | Provider | Overall | Best Categories | Recommendation |",
        "|-----:|-------|----------|--------:|-----------------|----------------|",
    ]
    for row in rows:
        cats = ", ".join(f"{k} {v:.2f}" for k, v in row.category_scores.items())
        lines.append(
            f"| {row.rank} | {row.model} | {row.provider} | {row.overall:.2f} | {cats} | {row.recommendation} |"
        )
    path.write_text("\n".join(lines) + "\n")


def generate_recommendations(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    items = recommend(results)
    lines = ["# Recommendations\n"]
    for rec in items:
        lines.append(f"## {rec.category}\n")
        lines.append(f"- **Model:** {rec.model}")
        lines.append(f"- **Provider:** {rec.provider}")
        lines.append(f"- **Score:** {rec.score:.2f}")
        lines.append(f"- **Overall score:** {rec.overall:.2f}")
        lines.append(f"- **Confidence:** {rec.confidence:.2f} ({rec.confidence_label})")
        lines.append(f"- **Weight contribution:** {rec.category_weight:.1f}")
        lines.append("- **Major contributing categories:**")
        for cat, val in rec.top_categories:
            lines.append(f"  - {cat}: {val:.2f}")
        lines.append("- **Reason:**")
        for reason in rec.reasons:
            lines.append(f"  - {reason}")
        if rec.rejection_reasons:
            lines.append("- **Alternatives rejected:**")
            for model, reasons in rec.rejection_reasons.items():
                lines.append(f"  - {model}:")
                for reason in reasons:
                    lines.append(f"    - {reason}")
        if rec.trade_offs:
            lines.append("- **Trade-offs:**")
            for to in rec.trade_offs:
                lines.append(f"  - {to}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def generate_team(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    roles = build_team(results)
    lines = ["# AI Engineering Team\n"]
    for role in roles:
        lines.append(f"## {role.role}\n")
        lines.append(f"- **Model:** {role.model}")
        lines.append(f"- **Provider:** {role.provider}")
        lines.append(f"- **Score:** {role.score:.2f}")
        lines.append(f"- **Confidence:** {role.confidence:.2f} ({role.confidence_label})")
        lines.append("- **Reason:**")
        for reason in role.reasons:
            lines.append(f"  - {reason}")
        if role.trade_offs:
            lines.append("- **Trade-offs:**")
            for to in role.trade_offs:
                lines.append(f"  - {to}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def generate_compare(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    db_path = kwargs.get("db_path")
    runs = _load_results_from_runs(2, db_path=db_path)
    if len(runs) >= 2:
        latest = runs[0]
        previous = runs[1]
    else:
        latest = results
        previous = results
    deltas = build_comparison(latest, previous)
    lines = ["# Comparison\n", "| Category | Previous | Latest | Delta | Trend |", "|----------|---------:|-------:|------:|-------|"]
    for delta in deltas.values():
        previous_str = f"{delta.previous:.2f}" if delta.previous is not None else "-"
        current_str = f"{delta.current:.2f}" if delta.current is not None else "-"
        delta_str = f"{delta.delta:+.2f}" if delta.delta is not None else "-"
        lines.append(f"| {delta.metric} | {previous_str} | {current_str} | {delta_str} | {delta.trend} |")
    path.write_text("\n".join(lines) + "\n")


def generate_trends(results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
    db_path = kwargs.get("db_path")
    runs = load_latest(5, db_path=db_path)
    if len(runs) < 2:
        path.write_text("# Trends\n\nNeed >=2 runs for trend analysis.\n")
        return
    trends = build_trends(runs)
    mv = best_value(runs[0])
    fa = fastest(runs[0])
    hq = highest_quality(runs[0])
    ms = most_stable(runs)
    lines = ["# Trends\n"]
    lines.append("## Model Trends\n")
    for key, entry in sorted(trends.items()):
        lines.append(
            f"- {entry.model} ({entry.provider}): {entry.trend}, overall change {entry.overall_change:+.2f}"
        )
        for cat, change in entry.category_changes.items():
            lines.append(f"  - {cat}: {change:+.2f}")
    lines.append("\n## Highlights\n")
    if mv:
        lines.append(f"- Best value: {mv.model} ({mv.provider}) — {mv.confidence_label}")
    if fa:
        lines.append(f"- Fastest: {fa.model} ({fa.provider})")
    if hq:
        lines.append(f"- Highest quality: {hq.model} ({hq.provider}) overall {hq.overall:.2f}")
    if ms:
        lines.append(f"- Most stable: {ms.model} ({ms.provider}) stability delta {ms.stability_delta}")
    path.write_text("\n".join(lines) + "\n")


def _parse_latency(result: Any) -> float | None:
    latency = None
    if hasattr(result, "metadata"):
        latency = result.metadata.get("latency_ms") if isinstance(result.metadata, dict) else None
    if latency is None and hasattr(result, "details"):
        latency = result.details.get("latency_ms") if isinstance(result.details, dict) else None
    if latency is None:
        return None
    try:
        return float(latency)
    except (TypeError, ValueError):
        return None


@register(PluginCategory.REPORTER, "leaderboard")
class LeaderboardReporter:
    plugin_name = "leaderboard"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_leaderboard(results, path)


@register(PluginCategory.REPORTER, "recommendations")
class RecommendationsReporter:
    plugin_name = "recommendations"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_recommendations(results, path)


@register(PluginCategory.REPORTER, "team")
class TeamReporter:
    plugin_name = "team"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_team(results, path)


@register(PluginCategory.REPORTER, "compare")
class CompareReporter:
    plugin_name = "compare"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_compare(results, path)


@register(PluginCategory.REPORTER, "trends")
class TrendsReporter:
    plugin_name = "trends"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        generate_trends(results, path)
