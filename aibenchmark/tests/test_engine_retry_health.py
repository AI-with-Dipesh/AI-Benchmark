from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.provider_health import reset_health_tracker, get_health_tracker
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, Score


class TestBenchEngineRetryHealthWiring:
    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_health_tracker()
        self.tracker = get_health_tracker()
        self.provider_name = "ollama"
        self.model = "llama3.2"
        self.benchmark_name = BenchmarkName("general")

        self.mock_provider = MagicMock()
        self.mock_benchmark = MagicMock()

        self.engine = BenchEngine()

    def test_retry_wired_to_health_tracker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._call_count = 0

        def fake_chat(*_args: object, **_kwargs: object) -> MagicMock:
            self._call_count += 1
            if self._call_count < 2:
                from aibenchmark.app.models import ResponseObject
                raise TimeoutError("timeout")
            from aibenchmark.app.models import ResponseObject
            return ResponseObject.model_construct(
                text="ok", latency_ms=10.0, tokens_in=1, tokens_out=1, raw={}, provider=self.provider_name, model=self.model
            )

        self.mock_provider.chat.side_effect = fake_chat
        self.mock_benchmark.run.return_value = BenchmarkResult(
            model=self.model, provider=self.provider_name, scores=[Score(benchmark=self.benchmark_name, raw=1.0, normalized=1.0, weight=10.0)]
        )

        monkeypatch.setattr(self.engine, "_init_provider", lambda _name: self.mock_provider)
        monkeypatch.setattr(self.engine.plugins, "get", lambda _cat, _name: lambda: self.mock_benchmark)

        result = self.engine.run_benchmark(self.provider_name, self.model, self.benchmark_name, [{"role": "user", "content": "hi"}])
        assert result.retry_count == 1
        assert self.tracker.get(self.provider_name).retry_rate == pytest.approx(1.0)

    def test_no_retry_keeps_zero_rate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aibenchmark.app.models import ResponseObject

        self.mock_provider.chat.return_value = ResponseObject.model_construct(
            text="ok", latency_ms=10.0, tokens_in=1, tokens_out=1, raw={}, provider=self.provider_name, model=self.model
        )
        self.mock_benchmark.run.return_value = BenchmarkResult(
            model=self.model, provider=self.provider_name, scores=[Score(benchmark=self.benchmark_name, raw=1.0, normalized=1.0, weight=10.0)]
        )

        monkeypatch.setattr(self.engine, "_init_provider", lambda _name: self.mock_provider)
        monkeypatch.setattr(self.engine.plugins, "get", lambda _cat, _name: lambda: self.mock_benchmark)

        result = self.engine.run_benchmark(self.provider_name, self.model, self.benchmark_name, [{"role": "user", "content": "hi"}])
        assert result.retry_count == 0
        assert self.tracker.get(self.provider_name).retry_rate == pytest.approx(0.0)
