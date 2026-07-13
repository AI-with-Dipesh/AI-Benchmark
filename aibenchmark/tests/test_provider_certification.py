from __future__ import annotations

import pytest

from aibenchmark.app.certification import ProviderCertificationLevel
from aibenchmark.app.cross_provider import CrossProviderBenchmark
from aibenchmark.app.provider_health import HealthTracker
from aibenchmark.app.provider_registry import ProviderRegistry
from aibenchmark.app.models import BenchmarkResult, BenchmarkName, Score, ProviderType


class TestProviderShutdown:
    def test_base_provider_shutdown_is_noop(self) -> None:
        from aibenchmark.interfaces.provider import BaseProvider

        class Dummy(BaseProvider):
            def connect(self) -> None:
                pass
            def list_models(self) -> list[str]:
                return []
            def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
                raise NotImplementedError

        d = Dummy(api_key="", base_url="")
        d.shutdown()  # should not raise


class TestProviderHealthExtensions:
    def test_median_latency_computed(self) -> None:
        tracker = HealthTracker(window_size=100)
        for i in range(5):
            tracker.record("p", float(i), True)
        h = tracker.get("p")
        assert h.median_latency_ms == pytest.approx(2.0)

    def test_median_latency_even_count(self) -> None:
        tracker = HealthTracker(window_size=100)
        for i in [1, 2, 3, 4]:
            tracker.record("p", float(i), True)
        h = tracker.get("p")
        assert h.median_latency_ms == pytest.approx(2.5)

    def test_connection_health_true_on_success(self) -> None:
        tracker = HealthTracker(window_size=100)
        h = tracker.record("p", 100.0, True)
        assert h.connection_health is True

    def test_connection_health_false_on_failure(self) -> None:
        tracker = HealthTracker(window_size=100)
        h = tracker.record("p", 100.0, False)
        assert h.connection_health is False


class TestProviderValidation:
    def test_validate_all_returns_dict(self) -> None:
        registry = ProviderRegistry()
        results = registry.validate_all()
        assert isinstance(results, dict)
        for name in registry.list_providers():
            assert name in results
            assert "valid" in results[name]
            assert "issues" in results[name]


class TestProviderCertification:
    def test_certify_returns_report(self) -> None:
        registry = ProviderRegistry()
        name = registry.list_providers()[0]
        report = registry.certify(name)
        assert report.provider_name == name
        assert report.certification_level in ProviderCertificationLevel
        assert 0.0 <= report.reliability_score <= 1.0
        assert 0.0 <= report.metadata_completeness <= 1.0
        assert 0.0 <= report.capability_detection_score <= 1.0

    def test_certify_all_providers(self) -> None:
        registry = ProviderRegistry()
        for name in registry.list_providers():
            report = registry.certify(name)
            assert report.certification_level in ProviderCertificationLevel

    def test_certification_levels_are_valid(self) -> None:
        levels = list(ProviderCertificationLevel)
        assert ProviderCertificationLevel.EXPERIMENTAL in levels
        assert ProviderCertificationLevel.BETA in levels
        assert ProviderCertificationLevel.STABLE in levels
        assert ProviderCertificationLevel.CERTIFIED in levels


class TestCrossProviderCategoryComparison:
    def test_compare_with_results_adds_category_comparison(self) -> None:
        bench = CrossProviderBenchmark()
        providers = ["ollama"]
        comparison = bench.compare_with_results(
            providers,
            {"ollama": ["llama3.2"]},
            [
                BenchmarkResult(
                    model="llama3.2",
                    provider=ProviderType.OLLAMA,
                    scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=0.9, weight=1.0)],
                ),
                BenchmarkResult(
                    model="llama3.2",
                    provider=ProviderType.OLLAMA,
                    scores=[Score(benchmark=BenchmarkName.CODING, raw=1.0, normalized=0.7, weight=1.0)],
                ),
            ],
        )
        assert "category_comparison" in comparison
        ollama_cats = comparison["category_comparison"]["ollama"]
        assert "general" in ollama_cats
        assert "coding" in ollama_cats
        assert ollama_cats["general"]["average"] == pytest.approx(0.9)
        assert ollama_cats["coding"]["average"] == pytest.approx(0.7)

    def test_compare_providers_without_results_has_no_category_comparison(self) -> None:
        bench = CrossProviderBenchmark()
        comparison = bench.compare_providers(["ollama"], {"ollama": []})
        assert "category_comparison" not in comparison

    def test_category_comparison_ignores_unknown_providers(self) -> None:
        bench = CrossProviderBenchmark()
        comparison = bench.compare_with_results(
            ["nvidia"],
            {"nvidia": []},
            [
                BenchmarkResult(
                    model="llama3.2",
                    provider=ProviderType.OLLAMA,
                    scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=1.0, weight=1.0)],
                ),
            ],
        )
        assert comparison["category_comparison"] == {"nvidia": {}}


class TestCLIValidationAndCertification:
    def test_validate_cli(self) -> None:
        from click.testing import CliRunner
        from aibenchmark.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["provider", "validate"])
        assert result.exit_code == 0

    def test_certify_cli(self) -> None:
        from click.testing import CliRunner
        from aibenchmark.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["provider", "certify"])
        assert result.exit_code == 0
