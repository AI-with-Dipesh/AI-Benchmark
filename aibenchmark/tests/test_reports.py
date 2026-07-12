from __future__ import annotations

from pathlib import Path
import json
import csv
import pytest

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score
from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.analytics import recommend, build_leaderboard, build_team, build_comparison, build_trends, best_value


def test_reports_generate_files(tmp_path: Path):
    engine = BenchEngine()
    results = [
        BenchmarkResult(
            model="model-a",
            provider=ProviderType.OLLAMA,
            scores=[Score(benchmark=BenchmarkName.LATENCY, raw=100.0, normalized=0.9, weight=1.0)],
            overall=0.9,
        )
    ]
    produced = engine.generate_reports(results, tmp_path, formats=["json", "csv", "md"])
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "results.md").exists()
    data = json.loads((tmp_path / "results.json").read_text())
    assert len(data) == 1
    assert data[0]["model"] == "model-a"


def test_reports_generate_analytics(tmp_path: Path):
    engine = BenchEngine()
    results = [
        BenchmarkResult(
            model="model-a",
            provider=ProviderType.OLLAMA,
            scores=[
                Score(benchmark=BenchmarkName.CODING, raw=100.0, normalized=0.8, weight=1.0),
                Score(benchmark=BenchmarkName.LATENCY, raw=1.0, normalized=0.9, weight=1.0),
            ],
            overall=0.85,
            metadata={"latency_ms": 120.0},
        )
    ]
    produced = engine.generate_reports(results, tmp_path, formats=["leaderboard", "recommendations", "team"])
    assert (tmp_path / "results.leaderboard").exists()
    assert (tmp_path / "results.recommendations").exists()
    assert (tmp_path / "results.team").exists()
    board = (tmp_path / "results.leaderboard").read_text()
    assert "model-a" in board

