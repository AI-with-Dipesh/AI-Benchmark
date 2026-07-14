from __future__ import annotations

from click.testing import CliRunner

from aibenchmark.cli import cli


def test_cli_route_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["route"])
    assert result.exit_code == 0


def test_cli_select_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["select", "coding"])
    assert result.exit_code != 0 or "Selected:" in result.output


def test_cli_fallback_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["fallback", "openrouter"])
    assert result.exit_code == 0


def test_cli_optimize_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["optimize"])
    assert result.exit_code == 0


def test_cli_parallel_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["parallel", "-p", "ollama"])
    assert result.exit_code != 0
    assert "disabled in configuration" in result.output


def test_cli_config_generate_litellm_smoke(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runner = CliRunner()
    out = tmp_path / "litellm.yaml"
    result = runner.invoke(cli, ["config", "generate-litellm", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()
