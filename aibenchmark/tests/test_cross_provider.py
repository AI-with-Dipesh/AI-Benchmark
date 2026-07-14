from __future__ import annotations


from aibenchmark.app.cross_provider import CrossProviderBenchmark


class TestCrossProviderBenchmark:
    def test_compare_returns_ranking(self) -> None:
        bench = CrossProviderBenchmark()
        result = bench.compare_providers(["nvidia", "ollama"], {"nvidia": [], "ollama": []})
        assert "overall_ranking" in result
        assert len(result["overall_ranking"]) == 2
        assert result["overall_ranking"][0]["provider"] in ("nvidia", "ollama")

    def test_compare_includes_capabilities(self) -> None:
        bench = CrossProviderBenchmark()
        result = bench.compare_providers(["nvidia"], {"nvidia": []})
        assert "nvidia" in result["capabilities"]

    def test_compare_includes_health(self) -> None:
        bench = CrossProviderBenchmark()
        result = bench.compare_providers(["openrouter"], {"openrouter": []})
        assert "openrouter" in result["health"]

    def test_ranking_sorted_descending(self) -> None:
        bench = CrossProviderBenchmark()
        result = bench.compare_providers(["nvidia", "openrouter", "ollama", "huggingface"], {})
        scores = [r["score"] for r in result["overall_ranking"]]
        assert scores == sorted(scores, reverse=True)
