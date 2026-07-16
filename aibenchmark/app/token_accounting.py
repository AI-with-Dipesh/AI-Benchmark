from __future__ import annotations

from typing import Callable, Sequence

from aibenchmark.app.models import BenchmarkResult, CostEntry, CostReport, TokenReport, TokenUsage


def _tokens(result: BenchmarkResult) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=int(result.prompt_tokens or 0),
        completion_tokens=int(result.completion_tokens or 0),
    )


def token_report(results: Sequence[BenchmarkResult]) -> TokenReport:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cost = 0.0
    tps_candidates: list[float] = []
    breakdown: dict[str, TokenUsage] = {}

    for r in results:
        usage = _tokens(r)
        prompt_tokens += usage.prompt_tokens
        completion_tokens += usage.completion_tokens
        total_tokens += usage.total_tokens
        cost += float(r.estimated_cost or 0.0)
        key = f"{r.provider.value}:{r.model}"
        prev = breakdown.get(key)
        if prev is None:
            breakdown[key] = usage
        else:
            breakdown[key] = TokenUsage(
                prev.prompt_tokens + usage.prompt_tokens,
                prev.completion_tokens + usage.completion_tokens,
            )
        latency_ms = _parse_latency(r)
        if latency_ms and latency_ms > 0 and usage.total_tokens > 0:
            tps_candidates.append(usage.total_tokens / (latency_ms / 1000.0))

    tokens_per_second = (sum(tps_candidates) / len(tps_candidates)) if tps_candidates else None
    return TokenReport(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        tokens_per_second=tokens_per_second,
        provider_model_breakdown=breakdown,
    )


def cost_report(results: Sequence[Sequence[BenchmarkResult]], price_lookup: Callable[[str, str], tuple[float, float]] | None = None) -> CostReport:
    total_cost = 0.0
    entries: list[CostEntry] = []
    by_provider: dict[str, float] = {}
    by_model: dict[str, float] = {}

    for run in results:
        for r in run:
            cost = float(r.estimated_cost or 0.0)
            total_cost += cost
            pp, cp = 0.0, 0.0
            if price_lookup is not None:
                try:
                    pp, cp = price_lookup(r.provider.value, r.model)
                except Exception:
                    pass
            entries.append(CostEntry(
                provider=r.provider.value,
                model=r.model,
                prompt_price_per_1k=pp,
                completion_price_per_1k=cp,
                prompt_tokens=int(r.prompt_tokens or 0),
                completion_tokens=int(r.completion_tokens or 0),
            ))
            key_provider = r.provider.value
            key_model = r.model
            by_provider[key_provider] = by_provider.get(key_provider, 0.0) + cost
            by_model[key_model] = by_model.get(key_model, 0.0) + cost

    return CostReport(total_cost=total_cost, entries=entries, by_provider=by_provider, by_model=by_model)


def _parse_latency(result: BenchmarkResult) -> float | None:
    latency = result.metadata.get("latency_ms") or result.details.get("latency_ms")
    if latency is None:
        return None
    try:
        return float(latency)
    except (TypeError, ValueError):
        return None
