from __future__ import annotations

from aibenchmark.app.models import ResponseObject, ProviderType
from aibenchmark.plugins.benchmarks.coding import CodingBenchmark
from aibenchmark.plugins.benchmarks.instruction import InstructionBenchmark
from aibenchmark.plugins.benchmarks.json import JsonBenchmark


def make_response(content: str) -> ResponseObject:
    return ResponseObject(provider=ProviderType.OLLAMA, model="demo", content=content, latency_ms=100.0)


def test_coding_benchmark_syntax_valid() -> None:
    result = CodingBenchmark().run(make_response("\n".join([
        "def add(a: int, b: int) -> int:",
        '    """Sum."""',
        "    return a + b",
    ])), prompt={"expected": "memoization"})
    assert result.details["syntax_ok"] is True


def test_json_benchmark_valid_json() -> None:
    result = JsonBenchmark().run(make_response('{"x":1}\n'))
    assert result.details.get("raw_score", 0.0) > 0.0


def test_instruction_benchmark_constraint_match() -> None:
    result = InstructionBenchmark().run(make_response("- a\n- b\nhello"), prompt={"expected": "hello"})
    assert result.details.get("constraint_score") == 1.0
