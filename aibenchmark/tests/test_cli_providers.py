from __future__ import annotations

import pytest

pytestmark = pytest.mark.skipif(True, reason="skip click tests in type-check mode")

try:
    from click.testing import CliRunner  # noqa: E402

    pytestmark = pytest.mark.skipif(False, reason="")
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False


class TestCLIProviderCommands:
    def test_providers_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.cli import cli
        monkeypatch.setenv("OLLAMA_API_KEY", "fake")
        runner = CliRunner()
        result = runner.invoke(cli, ["providers"])
        assert result.exit_code == 0
        assert "nvidia" in result.output or "ollama" in result.output

    def test_discover(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.cli import cli
        monkeypatch.setenv("OLLAMA_API_KEY", "fake")
        runner = CliRunner()
        result = runner.invoke(cli, ["discover"])
        assert result.exit_code == 0
        assert "Providers:" in result.output

    def test_capabilities_no_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["capabilities", "ollama"])
        assert result.exit_code == 0
        assert "ollama" in result.output.lower() or "==" in result.output

    def test_auth_no_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["auth"])
        assert result.exit_code == 0
        assert "ollama" in result.output

    def test_provider_compare_ranking(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["provider", "compare"])
        assert result.exit_code == 0
        assert "Overall Ranking" in result.output
