"""Sprint 11 coverage gap tests for production paths missed by earlier suites.

Focus: history lifecycle, model selector strategies, analytics edge cases, config validation.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aibenchmark.app.analytics import build_comparison, build_trends, recommend
from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.history import HistoryWriter, _connect, load_latest, load_run
from aibenchmark.app.model_selector import ModelSelector, RoutingContext
from aibenchmark.app.models import (
    BenchmarkName,
    BenchmarkResult,
    ProviderCapabilities,
    ProviderHealth,
    ProviderStatus,
    ProviderType,
    RoutingPlan,
    Score,
)
from unittest.mock import ANY


def _make_result(
    provider: str = "ollama",
    model: str = "llama3",
    benchmark: str = "coding",
    normalized: float = 0.8,
    overall: float | None = None,
    latency_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        provider=ProviderType(provider),
        model=model,
        scores=[Score(benchmark=BenchmarkName(benchmark), raw=normalized, normalized=normalized, weight=1.0)],
        overall=overall if overall is not None else normalized,
        metadata=metadata or {"timestamp": "2026-01-01T00:00:00+00:00", "latency_ms": latency_ms},
    )


# --- history.py lifecycle ---

class TestHistoryLifecycleCoverage:
    def test_connect_creates_parent_dir(self, tmp_path: Path) -> None:
        db = tmp_path / "nested" / "dir" / "history.db"
        conn = _connect(db)
        assert db.parent.exists()
        conn.close()

    def test_load_latest_empty_database(self, tmp_path: Path) -> None:
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        from aibenchmark.app.history import init_db
        init_db(conn)
        conn.close()
        runs = load_latest(1, db_path=db)
        assert runs == []

    def test_load_run_missing_raises_key_error(self, tmp_path: Path) -> None:
        db = tmp_path / "history.db"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        from aibenchmark.app.history import init_db
        init_db(conn)
        conn.close()
        with pytest.raises(KeyError):
            load_run(9999, db_path=db)

    def test_history_writer_context_manager_closes(self, tmp_path: Path) -> None:
        db = tmp_path / "cm.db"
        with HistoryWriter(db_path=db) as writer:
            run_id = writer.save_run([_make_result()])
            assert run_id > 0
        assert writer._conn is None

    def test_init_db_without_args_creates_schema(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        db_path = tmp_path / "default.db"
        monkeypatch.setattr("aibenchmark.app.history.DB_PATH", db_path)
        from aibenchmark.app.history import init_db
        init_db()
        assert db_path.exists()

    def test_json_default_with_datetime(self) -> None:
        from aibenchmark.app.history import _json_default
        from datetime import datetime
        result = _json_default(datetime(2026, 1, 1, 12, 0, 0))
        assert result == "2026-01-01T12:00:00"


# --- model_selector strategy coverage ---

class TestModelSelectorCoverage:
    def test_select_with_dict_context(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.routing = {"strategy": "cost_aware"}
        selector._registry = MagicMock()
        selector._health = MagicMock()
        candidates = [
            {
                "provider": "ollama",
                "model": "llama3",
                "estimated_cost": 0.01,
                "capability_score": 0.9,
                "health": ProviderHealth(provider_name="ollama", status=ProviderStatus.AVAILABLE),
                "history_score": 0.8,
            }
        ]
        plan = ModelSelector._cost_aware(candidates, RoutingContext(benchmark_name=BenchmarkName.CODING))
        assert plan.provider == "ollama"

    def test_round_robin_deterministic(self) -> None:
        candidates = [
            {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
        ]
        ctx = RoutingContext(benchmark_name=BenchmarkName.CODING, provider_name="a")
        plan = ModelSelector._round_robin(candidates, ctx)
        assert plan.provider == "a"
        assert plan.model == "m1"
        assert plan.fallback_providers == []

    def test_check_context_window_with_none(self) -> None:
        caps = ProviderCapabilities(context_window=None, max_output_tokens=1024)
        selector = ModelSelector.__new__(ModelSelector)
        result = selector._check_context_window("ollama", "llama3", 100, caps)
        assert result == (True, None)

    def test_history_score_exception_path(self, tmp_path: Path) -> None:
        db = tmp_path / "bad.db"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        from aibenchmark.app.history import init_db
        init_db(conn)
        conn.close()
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.routing = {}
        with patch(
            "aibenchmark.app.history.recent_category_performance",
            side_effect=Exception("db error"),
        ):
            score = selector._history_score("ollama", "llama3", RoutingContext(benchmark_name=BenchmarkName.GENERAL))
        assert score == 0.0


# --- analytics edge cases ---

class TestAnalyticsCoverage:
    def test_recommend_single_candidate(self) -> None:
        results = [_make_result(model="a", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
        recs = recommend(results)
        assert len(recs) == 1
        assert recs[0].model == "a"

    def test_build_trends_single_run(self) -> None:
        run = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
        trends = build_trends([run])
        assert trends == {}

    def test_build_comparison_mismatched_categories(self) -> None:
        run_a = [_make_result(benchmark="coding", overall=0.8)]
        run_b = [_make_result(benchmark="reasoning", overall=0.9)]
        deltas = build_comparison(run_a, run_b)
        assert isinstance(deltas, dict)


# --- config validation edge cases ---

class TestConfigCoverage:
    def test_provider_config_invalid_type_defensive(self) -> None:
        cfg = AppConfig.__new__(AppConfig)
        cfg.providers = {"bad": "not-a-dict"}
        result = cfg.provider_config("bad")
        assert result == {}


# --- model_selector coverage expansion ---

class TestModelSelectorAdditionalCoverage:
    def test_select_round_robin_strategy(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.routing = {"strategy": "round_robin"}
        selector._registry = MagicMock()
        selector._health = MagicMock()
        candidates = [
            {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
            {"provider": "b", "model": "m2", "estimated_cost": 0.2, "capability_score": 0.8, "health": None, "history_score": 0.4},
        ]
        with patch.object(selector, "_candidates", return_value=candidates):
            with patch.object(ModelSelector, "_round_robin", return_value=RoutingPlan(provider="a", model="m1", estimated_cost=0.1, rationale="rr", fallback_providers=[], fallback_models=[])) as mock_rr:
                plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING))
                mock_rr.assert_called_once_with(candidates, ANY)
                assert plan.provider == "a"

    def test_select_unknown_strategy_falls_back(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.routing = {"strategy": "unknown_strategy"}
        selector._registry = MagicMock()
        selector._health = MagicMock()
        candidates = [
            {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
        ]
        with patch.object(selector, "_candidates", return_value=candidates):
            with patch.object(ModelSelector, "_cost_aware", return_value=RoutingPlan(provider="a", model="m1", estimated_cost=0.1, rationale="fallback", fallback_providers=[], fallback_models=[])) as mock_cost:
                plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING))
                mock_cost.assert_called_once_with(candidates, ANY)
                assert plan.provider == "a"

    def test_select_cost_ceiling_exceeded(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector._registry = MagicMock()
        selector._health = MagicMock()
        candidates = [
            {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
        ]
        plan = RoutingPlan(provider="a", model="m1", estimated_cost=1.0, rationale="test", fallback_providers=[], fallback_models=[])
        with patch.object(selector, "_candidates", return_value=candidates):
            with patch.object(ModelSelector, "_cost_aware", return_value=plan):
                with pytest.raises(ConfigError, match="exceeds cost ceiling"):
                    selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING, max_cost=0.5))

    def test_check_context_window_exceeds(self) -> None:
        caps = ProviderCapabilities(context_window=100, max_output_tokens=50)
        selector = ModelSelector.__new__(ModelSelector)
        result = selector._check_context_window("ollama", "llama3", 100, caps)
        assert result == (False, ANY)
        assert result[1] is not None

    def test_candidates_history_exception_swallowed(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.routing = {}
        selector._registry = MagicMock()
        selector._health = MagicMock()
        with patch(
            "aibenchmark.app.history.recent_category_performance",
            side_effect=Exception("db error"),
        ):
            result = selector._candidates(RoutingContext(benchmark_name=BenchmarkName.CODING))
        assert result == []

    def test_candidates_value_error_provider_skipped(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector._registry = MagicMock()
        selector._registry.list_providers.return_value = ["bad_provider"]
        selector._registry.capabilities.side_effect = ValueError("unsupported")
        selector._health = MagicMock()
        result = selector._candidates(RoutingContext(benchmark_name=BenchmarkName.CODING))
        assert result == []

    def test_candidates_model_cost_exception(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.model_cost.side_effect = Exception("pricing error")
        selector._registry = MagicMock()
        selector._registry.list_providers.return_value = ["ollama"]
        selector._health = MagicMock()
        health = ProviderHealth(provider_name="ollama", status=ProviderStatus.AVAILABLE)
        selector._health.get.return_value = health
        caps = ProviderCapabilities(context_window=4096, max_output_tokens=1024)
        selector._registry.capabilities.return_value = caps
        selector._registry.list_models.return_value = ["llama3"]
        result = selector._candidates(RoutingContext(benchmark_name=BenchmarkName.CODING))
        assert len(result) == 1
        assert result[0]["estimated_cost"] == 0.0

    def test_capability_score_empty_required(self) -> None:
        caps = ProviderCapabilities(context_window=4096, max_output_tokens=1024)
        ctx = RoutingContext(benchmark_name=BenchmarkName.CODING, required_capabilities=[])
        assert ModelSelector._capability_score(caps, ctx) == 1.0

    def test_is_paid_exception_returns_false(self) -> None:
        selector = ModelSelector.__new__(ModelSelector)
        selector.config = MagicMock()
        selector.config.model_cost.side_effect = Exception("no pricing")
        assert selector._is_paid("ollama", "llama3") is False


# --- analytics additional coverage ---

class TestAnalyticsAdditionalCoverage:
    def test_build_comparison_regressed_trend(self) -> None:
        run_a = [_make_result(provider="ollama", benchmark="coding", normalized=0.4, overall=0.4, metadata={"timestamp": "2026-01-02T00:00:00+00:00"})]
        run_b = [_make_result(provider="ollama", benchmark="coding", normalized=0.9, overall=0.9, metadata={"timestamp": "2026-01-01T00:00:00+00:00"})]
        deltas = build_comparison(run_a, run_b)
        assert deltas["coding"].trend == "regressed"

    def test_build_trends_malformed_key_skips(self) -> None:
        run = [_make_result(model="no-colon", provider="ollama", benchmark="coding", overall=0.8, metadata={"timestamp": "2026-01-01T00:00:00+00:00"})]
        trends = build_trends([run])
        assert trends == {}

    def test_most_stable_empty_trends_returns_none(self) -> None:
        from aibenchmark.app.analytics import most_stable
        assert most_stable([]) is None


# --- engine additional coverage ---

class TestEngineAdditionalCoverage:
    def test_select_model_with_routingcontext(self) -> None:
        from aibenchmark.app.engine import BenchEngine
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.plugins = MagicMock()
        plan = RoutingPlan(provider="ollama", model="llama3", estimated_cost=0.1, rationale="test", fallback_providers=[], fallback_models=[])
        mock_selector = MagicMock(select=MagicMock(return_value=plan))
        mock_strategy_cls = MagicMock(return_value=mock_selector)
        with patch.object(engine, "_get_strategy", return_value=mock_strategy_cls):
            result = engine.select_model(RoutingContext(benchmark_name=BenchmarkName.CODING))
            assert result == plan.__dict__

    def test_select_model_with_dict_context(self) -> None:
        from aibenchmark.app.engine import BenchEngine
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        plan = RoutingPlan(provider="ollama", model="llama3", estimated_cost=0.1, rationale="test", fallback_providers=[], fallback_models=[])
        mock_selector = MagicMock(select=MagicMock(return_value=plan))
        mock_strategy_cls = MagicMock(return_value=mock_selector)
        with patch.object(engine, "_get_strategy", return_value=mock_strategy_cls):
            result = engine.select_model({"benchmark_name": "coding"})
            assert result == plan.__dict__
