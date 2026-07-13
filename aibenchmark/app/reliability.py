from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from aibenchmark.app.models import BenchmarkResult, ReliabilityEntry, ReliabilityReport, StatisticSummary


def _key(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def build_reliability(runs: Sequence[Sequence[BenchmarkResult]]) -> ReliabilityReport:
    buckets: dict[str, dict[str, list[BenchmarkResult]]] = defaultdict(lambda: defaultdict(list))
    for run_idx, run in enumerate(runs):
        for r in run:
            key = _key(r.provider.value, r.model)
            buckets[key]["results"].append(r)

    entries: dict[str, ReliabilityEntry] = {}
    provider_success_rates: dict[str, list[float]] = defaultdict(list)
    for key, data in buckets.items():
        success_count = 0
        failure_count = 0
        timeout_count = 0
        retry_count = 0
        total_latency_ms = 0.0
        latencies: list[float] = []
        for r in data["results"]:
            status = r.metadata.get("status", "success")
            latency = _parse_latency(r)
            if status == "success":
                success_count += 1
                if latency is not None:
                    total_latency_ms += latency
                    latencies.append(latency)
            else:
                failure_count += 1
            if r.timeout_status is not None:
                timeout_count += 1
            retry_count += r.retry_count
        entry = ReliabilityEntry(
            provider=data["results"][0].provider.value,
            model=data["results"][0].model,
            success_count=success_count,
            failure_count=failure_count,
            timeout_count=timeout_count,
            retry_count=retry_count,
            total_latency_ms=total_latency_ms,
            latency_samples=tuple(latencies),
        )
        entries[key] = entry
        provider_success_rates[entry.provider].append(entry.success_rate)

    availability = {provider: (sum(vals) / len(vals) if vals else 0.0) for provider, vals in provider_success_rates.items()}
    return ReliabilityReport(entries=entries, provider_availability=availability)


def summarize_latency(latencies: Sequence[float]) -> StatisticSummary | None:
    if not latencies:
        return None
    return StatisticSummary.from_values(list(latencies))


def _parse_latency(result: BenchmarkResult) -> float | None:
    latency = result.metadata.get("latency_ms") or result.details.get("latency_ms")
    if latency is None:
        return None
    try:
        return float(latency)
    except (TypeError, ValueError):
        return None
