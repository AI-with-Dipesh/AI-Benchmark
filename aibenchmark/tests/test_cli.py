from __future__ import annotations

from pathlib import Path

import aibenchmark.app.history as history_module
from click.testing import CliRunner
from aibenchmark.app.history import save_run
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score
from aibenchmark.cli import cli


def test_cli_governance_command_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["governance", "--help"])
    assert result.exit_code == 0
    assert "governance" in result.output.lower()


def test_cli_explain_command_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--help"])
    assert result.exit_code == 0


def test_cli_governance_generates_report(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "history.db"
    results = [
        BenchmarkResult(
            model="test-model",
            provider=ProviderType.OLLAMA,
            scores=[
                Score(
                    benchmark=BenchmarkName.CODING,
                    raw=0.8,
                    normalized=0.8,
                    weight=1.0,
                    weighted=0.8,
                )
            ],
            overall=0.8,
            details={},
            metadata={"timestamp": "2026-01-01T00:00:00+00:00"},
        )
    ]
    save_run(results, db_path=db_path)
    monkeypatch.setattr(history_module, "DB_PATH", db_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["governance", "--out", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "results.governance").exists()
    assert "Governance Report" in (tmp_path / "results.governance").read_text()

