from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Sequence

from aibenchmark.app.models import BenchmarkResult


@dataclass(frozen=True)
class Recommendation:
    category: str
    model: str
    provider: str
    confidence: float
    confidence_label: str
    reasons: list[str]
    score: float = 0.0
    latency_ms: float | None = None
    reliability: float | None = None
    trade_offs: list[str] = field(default_factory=list)
    overall: float = 0.0
    category_weight: float = 1.0
    rejection_reasons: dict[str, list[str]] = field(default_factory=dict)
    top_categories: list[tuple[str, float]] = field(default_factory=list)


@dataclass(frozen=True)
class TeamRole:
    role: str
    model: str
    provider: str
    confidence: float
    confidence_label: str
    reasons: list[str]
    score: float = 0.0
    trade_offs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    model: str
    provider: str
    overall: float
    category_scores: dict[str, float]
    latency_ms: float | None
    recommendation: str = ""


@dataclass(frozen=True)
class TrendEntry:
    model: str
    provider: str
    overall_change: float
    category_changes: dict[str, float]
    latency_delta: float | None
    stability_delta: float | None
    trend: str


@dataclass(frozen=True)
class ComparisonDelta:
    metric: str
    current: float | None
    previous: float | None
    delta: float | None
    trend: str


def _results_by_model(results: Sequence[BenchmarkResult]) -> dict[str, BenchmarkResult]:
    grouped: dict[str, BenchmarkResult] = {}
    for r in results:
        key = f"{r.provider.value}:{r.model}"
        if key not in grouped or r.overall > grouped[key].overall:
            grouped[key] = r
    return grouped


def _category_score(results: Sequence[BenchmarkResult], category: str) -> tuple[str, str, float, float | None]:
    best_model = ""
    best_provider = ""
    best_score = -math.inf
    best_latency: float | None = None
    for r in results:
        for s in r.scores:
            if s.benchmark.value == category and s.normalized > best_score:
                best_model = r.model
                best_provider = r.provider.value
                best_score = s.normalized
                best_latency = r.metadata.get("latency_ms") or r.details.get("latency_ms") or None
    return best_model, best_provider, best_score, best_latency


def _reliability_score(result: BenchmarkResult) -> float | None:
    for s in result.scores:
        if s.benchmark.value == "reliability":
            return s.normalized
    if "validation_summary" in result.details:
        return float(result.details["validation_summary"])  # type: ignore[arg-type]
    return None


def _confidence_label(value: float) -> str:
    if value >= 0.8:
        return "High"
    if value >= 0.55:
        return "Medium"
    return "Low"


def recommend(results: Sequence[BenchmarkResult]) -> list[Recommendation]:
    if not results:
        return []

    models_by_provider_model = _results_by_model(results)
    eligible = [r for key, r in models_by_provider_model.items() if r.scores]
    recommendations: list[Recommendation] = []
    categories: set[str] = set()
    for r in results:
        for s in r.scores:
            categories.add(s.benchmark.value)

    for category in sorted(categories):
        candidates: list[tuple[float, BenchmarkResult, list[str], float | None, float | None]] = []
        for r in eligible:
            score = next((s.normalized for s in r.scores if s.benchmark.value == category), None)
            if score is None:
                continue
            latency = _parse_latency(r)
            reliability = _reliability_score(r)
            reasons: list[str] = []
            if score == max(
                next((s.normalized for s in er.scores if s.benchmark.value == category), -math.inf)
                for er in eligible
                if any(s.benchmark.value == category for s in er.scores)
            ):
                reasons.append("Highest category score")
            if latency is not None and latency < 200:
                reasons.append("Low latency")
            rel = _reliability_score(r)
            if rel is not None and rel >= 0.9:
                reasons.append("High reliability")
            if r.overall >= 0.85 and category in {s.benchmark.value for s in r.scores}:
                reasons.append("Strong all-round performance")
            if not reasons:
                reasons.append("Best available score for category")
            candidates.append((score, r, reasons, latency, reliability))
        if not candidates:
            continue
        candidates.sort(key=lambda t: t[0], reverse=True)
        best_score, best_result, best_reasons, best_latency, best_reliability = candidates[0]
        trade_offs = [
            f"{r.model} ({r.provider.value}) score={score:.2f}"
            for score, r, _, _, _ in candidates[1:3]
        ]
        confidence = _build_confidence(best_score, best_result, category, candidates, models_by_provider_model)
        top_categories = sorted(
            ((s.benchmark.value, s.normalized) for s in best_result.scores),
            key=lambda t: t[1],
            reverse=True,
        )[:3]
        weight = next((s.weight for s in best_result.scores if s.benchmark.value == category), 1.0)
        rej: dict[str, list[str]] = {}
        for alt_score, alt_result, _, alt_latency, alt_reliability in candidates[1:]:
            alt_reasons: list[str] = []
            if alt_score < best_score:
                alt_reasons.append(f"Lower category score ({alt_score:.2f} vs {best_score:.2f})")
            if alt_latency is not None and best_latency is not None and alt_latency > best_latency:
                alt_reasons.append(f"Higher latency ({alt_latency:.0f}ms vs {best_latency:.0f}ms)")
            if alt_reliability is not None and best_reliability is not None and alt_reliability < best_reliability:
                alt_reasons.append(f"Lower reliability ({alt_reliability:.2f} vs {best_reliability:.2f})")
            rej[alt_result.model] = alt_reasons
        recommendations.append(
            Recommendation(
                category=category,
                model=best_result.model,
                provider=best_result.provider.value,
                confidence=round(confidence, 2),
                confidence_label=_confidence_label(confidence),
                reasons=best_reasons,
                score=round(best_score, 4),
                latency_ms=best_latency,
                reliability=best_reliability,
                trade_offs=trade_offs,
                overall=round(best_result.overall, 4),
                category_weight=round(weight, 4),
                rejection_reasons=rej,
                top_categories=top_categories,
            )
        )
    return recommendations


def _parse_latency(result: BenchmarkResult) -> float | None:
    latency = result.metadata.get("latency_ms") or result.details.get("latency_ms")
    if latency is None:
        return None
    try:
        return float(latency)
    except (TypeError, ValueError):
        return None


def _build_confidence(score: float, result: BenchmarkResult, category: str, candidates: list[tuple[float, BenchmarkResult, list[str], float | None, float | None]], by_key: dict[str, BenchmarkResult]) -> float:
    base = min(score, 1.0) * 0.7
    score_gap = 0.0
    if len(candidates) > 1:
        score_gap = (candidates[0][0] - candidates[1][0]) * 0.15
    reliability = 0.0
    rel = _reliability_score(result)
    if rel is not None:
        reliability = rel * 0.1
    history = 0.0
    key = f"{result.provider.value}:{result.model}"
    if key in by_key and by_key[key].scores:
        history = 0.05
    return min(1.0, max(0.0, base + score_gap + reliability + history))


def build_team(results: Sequence[BenchmarkResult]) -> list[TeamRole]:
    recommendations = recommend(results)
    if not recommendations:
        return []

    team_specs: list[tuple[str, str | None, Callable[[BenchmarkResult], float], list[str], bool]] = [
        ("Main", None, lambda r: r.overall, ["Highest overall score"], False),
        ("Coding", "coding", lambda r: next((s.normalized for s in r.scores if s.benchmark.value == "coding"), 0.0), ["Top coding score"], False),
        ("Debugging", "debugging", lambda r: next((s.normalized for s in r.scores if s.benchmark.value == "debugging"), 0.0), ["Top debugging score"], False),
        ("Reasoning", "reasoning", lambda r: next((s.normalized for s in r.scores if s.benchmark.value == "reasoning"), 0.0), ["Top reasoning score"], False),
        ("Research", "research", lambda r: next((s.normalized for s in r.scores if s.benchmark.value == "research"), 0.0), ["Top research score"], False),
        ("Review", "code_review", lambda r: next((s.normalized for s in r.scores if s.benchmark.value == "code_review"), 0.0), ["Top review score"], False),
        ("Fast", None, lambda r: _parse_latency(r) or 9999.0, ["Lowest latency"], True),
        ("Fallback", None, lambda r: max((s.normalized for s in r.scores), default=0.0), ["Highest minimum score across categories"], True),
    ]

    by_key = _results_by_model(results)
    candidates = list(by_key.values())
    if not candidates:
        return []

    roles: list[TeamRole] = []
    for role_name, category, scorer, reason_template, reverse in team_specs:
        candidates_sorted = sorted(candidates, key=scorer, reverse=not reverse)
        best = candidates_sorted[0]
        score = scorer(best)
        if category:
            score = next((s.normalized for s in best.scores if s.benchmark.value == category), score)
        confidence = min(1.0, max(0.0, 0.5 + float(score) * 0.5))
        trade_offs = [
            f"{r.model} ({r.provider.value}) score={scorer(r):.2f}"
            for r in candidates_sorted[1:3]
        ]
        roles.append(
            TeamRole(
                role=role_name,
                model=best.model,
                provider=best.provider.value,
                confidence=round(confidence, 2),
                confidence_label=_confidence_label(confidence),
                reasons=list(reason_template),
                score=round(float(score), 4),
                trade_offs=trade_offs,
            )
        )
    return roles


def build_leaderboard(results: Sequence[BenchmarkResult]) -> list[LeaderboardEntry]:
    by_key = _results_by_model(results)
    rows: list[LeaderboardEntry] = []
    ranked = sorted(by_key.values(), key=lambda r: r.overall, reverse=True)
    for idx, r in enumerate(ranked, start=1):
        score_map: dict[str, float] = {}
        for s in r.scores:
            score_map[s.benchmark.value] = round(s.normalized, 4)
        latency = _parse_latency(r)
        recommendation = _leaderboard_recommendation_string(r)
        rows.append(
            LeaderboardEntry(
                rank=idx,
                model=r.model,
                provider=r.provider.value,
                overall=round(r.overall, 4),
                category_scores=score_map,
                latency_ms=latency,
                recommendation=recommendation,
            )
        )
    return rows


def _leaderboard_recommendation_string(result: BenchmarkResult) -> str:
    latency = _parse_latency(result)
    best_cats = [f"{s.benchmark.value} ({s.normalized:.2f})" for s in sorted(result.scores, key=lambda s: s.normalized, reverse=True)[:2]]
    parts = ["Best categories: " + ", ".join(best_cats)]
    if latency is not None:
        parts.append(f"latency {latency:.0f} ms")
    if result.overall >= 0.9:
        parts.append("Elite overall")
    elif result.overall >= 0.75:
        parts.append("Strong overall")
    return "; ".join(parts)


def build_comparison(run_a: Sequence[BenchmarkResult], run_b: Sequence[BenchmarkResult], label_a: str = "Latest", label_b: str = "Previous") -> dict[str, ComparisonDelta]:
    deltas: dict[str, ComparisonDelta] = {}
    categories = sorted({s.benchmark.value for r in run_a for s in r.scores} | {s.benchmark.value for r in run_b for s in r.scores})
    for category in categories:
        scored_a = [(r.model, r.provider.value, s.normalized) for r in run_a for s in r.scores if s.benchmark.value == category]
        scored_b = [(r.model, r.provider.value, s.normalized) for r in run_b for s in r.scores if s.benchmark.value == category]
        val_a = max((score for _, _, score in scored_a), default=None)
        val_b = max((score for _, _, score in scored_b), default=None)
        delta = (val_a - val_b) if val_a is not None and val_b is not None else None
        if delta is None:
            trend = "new" if val_a is not None else "removed"
        elif delta > 0.01:
            trend = "improved"
        elif delta < -0.01:
            trend = "regressed"
        else:
            trend = "flat"
        deltas[category] = ComparisonDelta(
            metric=category,
            current=val_a,
            previous=val_b,
            delta=round(delta, 4) if delta is not None else None,
            trend=trend,
        )
    return deltas


def build_trends(runs: Sequence[Sequence[BenchmarkResult]]) -> dict[str, TrendEntry]:
    if not runs:
        return {}
    combined: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for run in runs:
        for r in _results_by_model(run).values():
            combined[f"{r.provider.value}:{r.model}"].append(r)
    trends: dict[str, TrendEntry] = {}
    for key, items in combined.items():
        by_time = sorted(items, key=lambda r: r.metadata.get("timestamp", ""))
        if len(by_time) < 2:
            continue
        current = by_time[-1]
        previous = by_time[-2]
        try:
            provider, model = key.split(":", 1)
        except ValueError:
            continue
        category_changes: dict[str, float] = {}
        categories = sorted({s.benchmark.value for r in by_time for s in r.scores})
        for cat in categories:
            cur = next((s.normalized for s in current.scores if s.benchmark.value == cat), None)
            prev = next((s.normalized for s in previous.scores if s.benchmark.value == cat), None)
            if cur is not None and prev is not None:
                category_changes[cat] = round(cur - prev, 4)
        overall_change = round(current.overall - previous.overall, 4)
        cur_latency = _parse_latency(current)
        prev_latency = _parse_latency(previous)
        latency_delta: float | None = None
        if cur_latency is not None and prev_latency is not None:
            latency_delta = round(cur_latency - prev_latency, 2)
        stability = _stability_trend(by_time)
        trend = "improving"
        if overall_change < -0.01:
            trend = "regressing"
        elif overall_change <= 0.01 and not category_changes:
            trend = "stable"
        trends[key] = TrendEntry(
            model=model,
            provider=provider,
            overall_change=overall_change,
            category_changes=category_changes,
            latency_delta=latency_delta,
            stability_delta=stability,
            trend=trend,
        )
    return trends


def _stability_trend(items: list[BenchmarkResult]) -> float | None:
    if len(items) < 2:
        return None
    deltas = []
    for i in range(1, len(items)):
        deltas.append(abs(items[i].overall - items[i - 1].overall))
    return round(sum(deltas) / len(deltas), 4) if deltas else None


def best_value(results: Sequence[BenchmarkResult]) -> Recommendation | None:
    candidates = [r for r in _results_by_model(results).values() if r.scores]
    if not candidates:
        return None
    scored = []
    for r in candidates:
        score = r.overall
        latency = _parse_latency(r) or 300
        value = score * 1000 / max(1, latency)
        scored.append((value, score, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    value, score, best = scored[0]
    confidence = min(1.0, max(0.3, value / 5))
    return Recommendation(
        category="value",
        model=best.model,
        provider=best.provider.value,
        confidence=round(confidence, 2),
        confidence_label=_confidence_label(confidence),
        reasons=[f"Best score-per-ms ratio ({value:.2f})"],
        score=round(score, 4),
        latency_ms=_parse_latency(best),
    )


def most_stable(runs: Sequence[Sequence[BenchmarkResult]]) -> TrendEntry | None:
    trends = build_trends(runs)
    stable = [t for t in trends.values() if t.stability_delta is not None]
    if not stable:
        return None
    stable.sort(key=lambda t: t.stability_delta or 0.0)
    return stable[0]


def fastest(results: Sequence[BenchmarkResult]) -> BenchmarkResult | None:
    cands = [r for r in _results_by_model(results).values() if _parse_latency(r) is not None]
    cands.sort(key=lambda r: _parse_latency(r) or 9999.0)  # type: ignore[arg-type]
    return cands[0] if cands else None


def highest_quality(results: Sequence[BenchmarkResult]) -> BenchmarkResult | None:
    cands = [r for r in _results_by_model(results).values() if r.scores]
    cands.sort(key=lambda r: r.overall, reverse=True)
    return cands[0] if cands else None
