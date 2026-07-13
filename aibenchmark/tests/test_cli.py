from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

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


def test_cli_governance_generates_report(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["governance", "--out", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "results.governance").exists()
    assert "Governance Report" in (tmp_path / "results.governance").read_text()

