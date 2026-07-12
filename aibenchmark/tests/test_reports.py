from __future__ import annotations

from pathlib import Path
import json
import pytest

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score
from aibenchmark.app.engine import BenchEngine


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
