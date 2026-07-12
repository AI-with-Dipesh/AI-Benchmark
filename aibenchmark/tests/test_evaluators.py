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


def make_evaluator(category: str, response: str = ""):
    return {
        "coding": CodeEvaluator("coding", {}, response),
        "debugging": DebuggingEvaluator("debugging", {}, response),
        "code_review": CodeReviewEvaluator("code_review", {}, response),
        "general": GeneralEvaluator("general", {}, response),
        "instruction": InstructionEvaluator("instruction", {"expected": "hello"}, response),
        "json": JsonEvaluator("json", {}, response),
        "reasoning": ReasoningEvaluator("reasoning", {"expected": "steps"}, response),
        "research": ResearchEvaluator("research", {"expected": "summary"}, response),
    }[category]


@pytest.mark.parametrize(
    "category,response",
    [
        ("coding", "def add(a: int, b: int) -> int:\n    \"\"\"Sum.\"\"\"\n    return a + b\n"),
        ("debugging", "Root cause is null reference. Fix by adding guard clause: if obj is None: return\n"),
        ("code_review", "Security: SQL injection risk. Prefer parameterized queries. Performance: Rebuild at O(n).\n"),
        ("general", "Concise answer to your question: the pipeline is fast and clear.\n"),
        ("instruction", "- Step 1\n- Step 2\nhello\n"),
        ("json", '{"a":1,"b":2}\n'),
        ("reasoning", "Step 1: parse. Step 2: transform. Step 3: load. Because each stage is isolated.\n"),
        ("research", "Key point: distributed tracing cuts latency. Secondary point: use OTel for sampling.\n"),
    ],
)
def test_evaluator_normalized_range(category: str, response: str) -> None:
    result = make_evaluator(category, response).evaluate()
    assert 0.0 <= result.score <= 1.0
    assert 0.0 <= result.normalized <= 1.0


def test_json_evaluator_valid_min_max() -> None:
    ev = JsonEvaluator("json", {}, '{"x":10}\n')
    result = ev.evaluate()
    assert result.metadata["valid"] is True
    assert result.normalized >= 0.0


def test_json_evaluator_invalid() -> None:
    ev = JsonEvaluator("json", {}, "not json")
    result = ev.evaluate()
    assert result.metadata["valid"] is False
    assert result.score == 0.0


def test_instruction_evaluator_exact_constraint() -> None:
    ev = InstructionEvaluator("instruction", {"expected": "hello"}, "hello world")
    result = ev.evaluate()
    assert result.metadata["constraint_score"] == 1.0
