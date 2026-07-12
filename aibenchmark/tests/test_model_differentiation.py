from __future__ import annotations

import pytest

from aibenchmark.app.evaluation import (
    CodeEvaluator,
    CodeReviewEvaluator,
    DebuggingEvaluator,
    GeneralEvaluator,
    InstructionEvaluator,
    JsonEvaluator,
    ReasoningEvaluator,
    ResearchEvaluator,
)


def _run(category: str, response: str, expected: str = "root cause, fix, test"):
    mapping = {
        "coding": CodeEvaluator,
        "debugging": DebuggingEvaluator,
        "general": GeneralEvaluator,
        "instruction": InstructionEvaluator,
        "json": JsonEvaluator,
        "reasoning": ReasoningEvaluator,
        "research": ResearchEvaluator,
        "code_review": CodeReviewEvaluator,
    }
    return mapping[category](category, {"expected": expected}, response).evaluate()


def _assert_descending(scores: list[float]) -> None:
    for idx in range(1, len(scores)):
        assert scores[idx] <= scores[idx - 1] + 1e-6, f"Expected descending scores at positions {idx-1},{idx}"


def test_model_differentiation_coding() -> None:
    excellent = "\n".join([
        "def add(a: int, b: int) -> int:",
        '    """Return sum of two ints."""',
        "    return a + b",
    ])
    good = "\n".join([
        "def add(a, b):",
        "    return a + b",
    ])
    poor = "def add(a, b): return +"
    scores = [_run("coding", r, "function, type hints, docstring").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_debugging() -> None:
    excellent = "Root cause: null reference. Fix by adding guard clause.\n```python\nif obj is None:\n    return\n```"
    good = "Root cause appears to be null reference. Fix by checking for null.\n"
    poor = "Something is wrong maybe."
    scores = [_run("debugging", r, "root cause, fix").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_research() -> None:
    excellent = "Key point: distributed tracing cuts latency. Secondary point: OpenTelemetry for sampling. [1] https://example.com\n" * 2
    good = "Summary: distributed tracing helps latency. Use OpenTelemetry.\n"
    poor = "Tracing is useful."
    scores = [_run("research", r, "distributed tracing, latency, OpenTelemetry").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_reasoning() -> None:
    excellent = "Step 1: parse input. Step 2: validate schema. Step 3: load data. Because each stage isolates errors.\n"
    good = "Parse, validate, load.\n"
    poor = "Do it."
    scores = [_run("reasoning", r, "step, parse, validate, load").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_code_review() -> None:
    excellent = "Security: SQL injection risk detected. Add parameterized queries. Performance: Rebuild at O(n). Architecture: split parser from loader. Severity: high."
    good = "Security: possible SQL injection issue. Performance: maybe slow. Maintainability could be improved."
    poor = "Looks fine."
    scores = [_run("code_review", r, "security, performance, architecture").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_json() -> None:
    excellent = '{"sorted": true, "items": [1, 2, 3]}\n'
    good = '{"items":[1,2,3]}\n'
    poor = "not json"
    scores = [_run("json", r).score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]


def test_model_differentiation_instruction() -> None:
    excellent = "- Step 1\n- Step 2\n- Step 3\nhello\n"
    good = "Step 1 Step 2 Step 3\nhello\n"
    poor = "Here is something without constraints."
    scores = [_run("instruction", r, "hello").score for r in [excellent, good, poor]]
    _assert_descending(scores)
    assert scores[0] > scores[-1]
