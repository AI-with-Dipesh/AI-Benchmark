from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.analytics import (
    build_comparison,
    build_team,
    build_trends,
    recommend,
    _reliability_score,
)
from aibenchmark.app.history import load_latest, save_run
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(provider: str, model: str, overall: float, scores: dict[str, float], latency_ms: float | None = None, reliability: float | None = None, timestamp: str | None = None) -> BenchmarkResult:
    meta: dict[str, Any] = {"latency_ms": latency_ms}
    if timestamp:
        meta["timestamp"] = timestamp
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=BenchmarkName(cat), raw=val, normalized=val, weight=1.0) for cat, val in scores.items()],
        overall=overall,
        metadata=meta,
        details={"validation_summary": reliability} if reliability is not None else {},
    )


def test_build_trends_skips_malformed_key(tmp_path: Path) -> None:
    results = [
        _make_result("openai", "gpt", 0.8, {"coding": 0.8}, timestamp="2026-01-01T00:00:00+00:00"),
    ]
    db = tmp_path / "history.db"
    save_run(results, db_path=db)
    import sqlite3
    conn = sqlite3.connect(db)
    conn.execute("UPDATE benchmark_scores SET benchmark='bad:key:extra' WHERE run_id=1")
    conn.commit()
    conn.close()
    loaded = load_latest(1, db_path=db)
    trends = build_trends(loaded)
    assert "openai:gpt" in trends or trends == {}


def test_build_trends_single_run_no_trend() -> None:
    results = [_make_result("openai", "gpt", 0.8, {"coding": 0.8})]
    assert build_trends([results]) == {}


def test_recommend_trade_offs_populated() -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    recs = recommend(results)
    coding = next(r for r in recs if r.category == "coding")
    assert len(coding.trade_offs) == 1
    assert "a" in coding.trade_offs[0] or "b" in coding.trade_offs[0]


def test_build_team_trade_offs_populated() -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    roles = build_team(results)
    main = next(r for r in roles if r.role == "Main")
    assert len(main.trade_offs) == 1


def test_build_comparison_new_and_removed() -> None:
    old = [_make_result("openai", "m", 0.7, {"coding": 0.7})]
    new = [_make_result("openai", "m", 0.8, {"coding": 0.8, "reasoning": 0.9})]
    deltas = build_comparison(new, old)
    assert deltas["coding"].trend == "improved"
    assert deltas["reasoning"].trend == "new"
    assert deltas.get("debugging", None) is None


def test_reliability_score_from_details() -> None:
    r = _make_result("openai", "m", 0.8, {"coding": 0.8}, reliability=0.95)
    assert _reliability_score(r) == 0.95


# Sprint 5 coverage boost


def test_base_provider_stream_yields_content() -> None:
    from aibenchmark.interfaces.provider import BaseProvider
    from aibenchmark.app.models import ResponseObject, ProviderType

    class DummyProvider(BaseProvider):
        plugin_name = "dummy"

        def connect(self) -> None: ...
        def list_models(self) -> list[str]: ...
        def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
            return ResponseObject(provider=ProviderType.OLLAMA, model=model, content="ok", latency_ms=10.0, tokens_in=1, tokens_out=1)

    p = DummyProvider(api_key="k")
    chunks = list(p.stream("m", []))
    assert chunks == ["ok"]


def test_base_provider_invoke_alias() -> None:
    from aibenchmark.interfaces.provider import BaseProvider
    from aibenchmark.app.models import ResponseObject, ProviderType

    class DummyProvider(BaseProvider):
        plugin_name = "dummy"

        def connect(self) -> None: ...
        def list_models(self) -> list[str]: ...
        def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
            return ResponseObject(provider=ProviderType.OLLAMA, model=model, content="ok")

    p = DummyProvider(api_key="k")
    r = p.invoke("m", [])
    assert r.content == "ok"


def test_provider_compare_reporter_output(tmp_path: Path) -> None:
    from aibenchmark.plugins.reporters.provider_comparison import ProviderComparisonReporter
    rep = ProviderComparisonReporter()
    rep.generate([], tmp_path / "compare.md", providers=["nvidia"], models={"nvidia": []})
    txt = (tmp_path / "compare.md").read_text()
    assert "Provider Comparison Report" in txt


def test_provider_health_reporter_output(tmp_path: Path) -> None:
    from aibenchmark.plugins.reporters.provider_health import ProviderHealthReporter
    rep = ProviderHealthReporter()
    rep.generate([], tmp_path / "health.md")
    txt = (tmp_path / "health.md").read_text()
    assert "Health Report" in txt


def test_capabilities_reporter_output(tmp_path: Path) -> None:
    from aibenchmark.plugins.reporters.capabilities import CapabilitiesReporter
    rep = CapabilitiesReporter()
    rep.generate([], tmp_path / "caps.md")
    txt = (tmp_path / "caps.md").read_text()
    assert "Capabilities Report" in txt
