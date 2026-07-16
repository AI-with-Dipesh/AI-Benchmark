from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvalResult:
    raw: dict[str, Any]
    score: float
    normalized: float
    metadata: dict[str, Any]


class EvaluationError(Exception):
    """Raised when response evaluation fails."""


class BaseEvaluator:
    category: str = ""

    def __init__(self, benchmark_name: str, prompt: dict[str, Any], response: str) -> None:
        self.benchmark_name = benchmark_name
        self.prompt = prompt
        self.response = response

    def evaluate(self) -> EvalResult:
        raise NotImplementedError

    def _normalize(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        if maximum <= minimum:
            return 0.0
        value = max(minimum, min(maximum, value))
        return (value - minimum) / (maximum - minimum)


def _validate_python_syntax(code: str) -> tuple[bool, str | None]:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return False, str(exc)
    return True, None


def _has_type_hints(code: str) -> bool:
    return bool(re.search(r":\s*(int|str|list|dict|tuple|Any)\b", code)) or \
           bool(re.search(r"->\s*(int|str|list|dict|tuple|Any)", code))


def _has_docstrings(code: str) -> bool:
    return bool(re.search(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', code))


def _count_functions(code: str) -> int:
    return len(re.findall(r"\ndef\s+\w+", code))


def _cyclomatic_complexity(code: str) -> int:
    return code.count("if") + code.count("for") + code.count("while") + code.count("except") + 1


def _word_count(text: str) -> int:
    return len(text.split())


def _bullet_score(text: str) -> tuple[float, int]:
    bullet_count = len(re.findall(r"(^|\n)\s*[-*]\s+", text))
    line_count = text.count("\n") + 1 or 1
    score = min(1.0, (bullet_count + 1) / line_count)
    return score, bullet_count


def _constraint_score(text: str, expected: str | None) -> float:
    if not expected:
        return 0.0
    return 1.0 if expected.lower() in text.lower() else 0.0


def _expected_token_coverage(text: str, expected: str) -> float:
    text_tokens = set(re.split(r"\W+", text.lower()))
    expected_tokens = [t for t in re.split(r"\W+", expected.lower()) if t]
    if not expected_tokens:
        return 0.0
    return sum(1 for token in expected_tokens if token in text_tokens) / len(expected_tokens)


class CodeEvaluator(BaseEvaluator):
    category = "coding"

    def evaluate(self) -> EvalResult:
        raw = self.response or ""
        expected = (self.prompt.get("expected") or "")
        syntax_ok, syntax_error = _validate_python_syntax(raw)
        functions = _count_functions(raw)
        complexity = _cyclomatic_complexity(raw) if functions else 0

        score = 0.0
        if syntax_ok:
            score += 0.4
        score += 0.2 if _has_type_hints(raw) else 0.0
        score += 0.2 if _has_docstrings(raw) else 0.0
        score += 0.2 if complexity <= 5 else 0.0
        expected_score = _expected_token_coverage(raw, expected)
        score = min(1.0, score + expected_score * 0.3)

        metadata: dict[str, Any] = {
            "syntax_ok": syntax_ok,
            "functions": functions,
            "cyclomatic_complexity": complexity,
            "expected_score": expected_score,
        }
        if syntax_error:
            metadata["syntax_error"] = syntax_error

        return EvalResult(
            raw={"score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class DebuggingEvaluator(BaseEvaluator):
    category = "debugging"
    weights = {"objective": 0.6, "heuristic": 0.4}

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")

        root_cause_terms = ["root cause", "cause", "reason"]
        fix_terms = ["fix", "patch", "solution", "repair"]
        expected_tokens = [t for t in re.split(r"\W+", expected.lower()) if t]
        response_tokens = set(re.split(r"\W+", text.lower()))

        exact_root = bool(re.search(r"root\s+cause", text.lower()))
        exact_fix = bool(re.search(r"\bfix\b", text.lower()))
        expected_score: float = sum(1 for t in expected_tokens if t in response_tokens)
        expected_score = expected_score / len(expected_tokens) if expected_tokens else 0.0

        code_blocks = re.findall(r"```(?:[a-zA-Z]*\n)?([\s\S]*?)```", text)
        syntax_ok = True
        for block in code_blocks:
            ok, _ = _validate_python_syntax(block)
            if not ok:
                syntax_ok = False

        objective = min(1.0, exact_root * 0.25 + exact_fix * 0.25 + expected_score * 0.3 + (1.0 if syntax_ok else 0.0) * 0.2)

        root_score = 1.0 if any(term in text.lower() for term in root_cause_terms) else 0.0
        fix_score = 1.0 if any(term in text.lower() for term in fix_terms) else 0.0
        heuristic = min(1.0, root_score * 0.4 + fix_score * 0.4 + expected_score * 0.2)

        score = min(1.0, self.weights["objective"] * objective + self.weights["heuristic"] * heuristic)

        metadata = {
            "objective": objective,
            "heuristic": heuristic,
            "exact_root": exact_root,
            "exact_fix": exact_fix,
            "expected_score": expected_score,
            "syntax_ok": syntax_ok,
            "root_score": root_score,
            "fix_score": fix_score,
        }

        return EvalResult(
            raw={"objective": objective, "heuristic": heuristic, "score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class ResearchEvaluator(BaseEvaluator):
    category = "research"
    weights = {"objective": 0.55, "heuristic": 0.45}

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")
        expected_tokens = [t for t in re.split(r"\W+", expected.lower()) if t]
        response_tokens = set(re.split(r"\W+", text.lower()))

        citation_score = 1.0 if any(marker in text for marker in ["[", "]", "(", ")", "http"]) else 0.0
        structure_score = 1.0 if any(marker in text for marker in ["##", "###", "- ", "* ", "1."]) else 0.0
        expected_score: float = sum(1 for t in expected_tokens if t in response_tokens)
        expected_score = expected_score / len(expected_tokens) if expected_tokens else 0.0
        objective = min(1.0, expected_score * 0.45 + citation_score * 0.3 + structure_score * 0.25)

        key_point_terms = ["key", "summary", "important", "main"]
        heuristic_structure = 1.0 if any(term in text.lower() for term in key_point_terms) and len(text.split()) > 20 else 0.0
        heuristic = min(1.0, heuristic_structure * 0.45 + expected_score * 0.3 + citation_score * 0.25)

        score = min(1.0, self.weights["objective"] * objective + self.weights["heuristic"] * heuristic)

        metadata = {
            "objective": objective,
            "heuristic": heuristic,
            "citation_score": citation_score,
            "structure_score": structure_score,
            "expected_score": expected_score,
        }

        return EvalResult(
            raw={"objective": objective, "heuristic": heuristic, "score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class ReasoningEvaluator(BaseEvaluator):
    category = "reasoning"
    weights = {"objective": 0.55, "heuristic": 0.45}

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")
        expected_tokens = [t for t in re.split(r"\W+", expected.lower()) if t]
        response_tokens = set(re.split(r"\W+", text.lower()))

        step_tokens = ["step", "first", "second", "then", "because"]
        steps_score = 1.0 if any(term in text.lower() for term in step_tokens) else 0.0
        expected_score: float = sum(1 for t in expected_tokens if t in response_tokens)
        expected_score = expected_score / len(expected_tokens) if expected_tokens else 0.0
        contradiction_penalty = 0.0
        lowered = text.lower()
        if "not" in lowered and any(term in lowered for term in ["always", "never", "all", "every"]):
            contradiction_penalty = 0.1
        objective_steps = min(1.0, steps_score * 0.45 + expected_score * 0.4 - contradiction_penalty)
        objective = max(0.0, objective_steps)

        heuristic = min(1.0, steps_score * 0.5 + expected_score * 0.35 + (0.15 if len(text.split()) >= 18 else 0.0))

        score = min(1.0, self.weights["objective"] * objective + self.weights["heuristic"] * heuristic)

        metadata = {
            "objective": objective,
            "heuristic": heuristic,
            "steps_score": steps_score,
            "expected_score": expected_score,
            "contradiction_penalty": contradiction_penalty,
        }

        return EvalResult(
            raw={"objective": objective, "heuristic": heuristic, "score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class CodeReviewEvaluator(BaseEvaluator):
    category = "code_review"
    weights = {"objective": 0.55, "heuristic": 0.45}

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")
        expected_tokens = [t for t in re.split(r"\W+", expected.lower()) if t]
        response_tokens = set(re.split(r"\W+", text.lower()))
        expected_score: float = sum(1 for t in expected_tokens if t in response_tokens)
        expected_score = expected_score / len(expected_tokens) if expected_tokens else 0.0

        issue_types = ["sql", "xss", "injection", "complexity", "memory", "race", "auth", "permission"]
        covered = sum(1 for term in issue_types if term in text.lower())
        issue_coverage = covered / len(issue_types)

        security_terms = ["security", "vulnerability", "injection", "auth", "permission"]
        perf_terms = ["performance", "complexity", "O(n)", "optim", "cache"]
        security_score = 1.0 if any(term in text.lower() for term in security_terms) else 0.0
        perf_score = 1.0 if any(term in text.lower() for term in perf_terms) else 0.0

        objective = min(1.0, expected_score * 0.4 + issue_coverage * 0.35 + security_score * 0.15 + perf_score * 0.1)
        heuristic = min(1.0, security_score * 0.4 + perf_score * 0.3 + expected_score * 0.3)
        score = min(1.0, self.weights["objective"] * objective + self.weights["heuristic"] * heuristic)

        metadata = {
            "objective": objective,
            "heuristic": heuristic,
            "security_score": security_score,
            "perf_score": perf_score,
            "issue_coverage": issue_coverage,
            "expected_score": expected_score,
        }

        return EvalResult(
            raw={"objective": objective, "heuristic": heuristic, "score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class GeneralEvaluator(BaseEvaluator):
    category = "general"
    weights = {"objective": 0.6, "heuristic": 0.4}

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")

        required_sections = [section.strip() for section in expected.split(",") if section.strip()]
        present_sections = [section for section in required_sections if section.lower() in text.lower()]
        section_score = len(present_sections) / len(required_sections) if required_sections else 0.0

        coverage = _expected_token_coverage(text, expected)
        objective = min(1.0, section_score * 0.6 + coverage * 0.4)

        clarity = coverage
        conciseness = 1.0 - min(1.0, abs(_word_count(text) - 60) / 120)
        heuristic = min(1.0, clarity * 0.6 + conciseness * 0.4)

        score = min(1.0, self.weights["objective"] * objective + self.weights["heuristic"] * heuristic)

        metadata = {
            "objective": objective,
            "heuristic": heuristic,
            "clarity": clarity,
            "conciseness": conciseness,
            "section_score": section_score,
            "coverage": coverage,
        }

        return EvalResult(
            raw={"objective": objective, "heuristic": heuristic, "score": score, **metadata},
            score=score,
            normalized=self._normalize(score),
            metadata=metadata,
        )


class JsonEvaluator(BaseEvaluator):
    category = "json"

    def _extract_json(self, text: str) -> tuple[Any, str | None]:
        if not text:
            return None, "empty response"
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(text)
        except json.JSONDecodeError:
            return None, "invalid json"
        return obj, None

    def evaluate(self) -> EvalResult:
        obj, err = self._extract_json(self.response)
        if err or obj is None:
            return EvalResult(raw={"error": err or "unknown"}, score=0.0, normalized=0.0, metadata={"valid": False})

        complexity = len(json.dumps(obj, ensure_ascii=False))
        lines = self.response.count("\n") + 1
        raw_score = 0.6 + min(0.25, max(0.0, 0.0075 * complexity)) + min(0.15, max(0.0, 0.03 * lines))
        raw_score = min(1.0, raw_score)

        return EvalResult(
            raw={"valid": True, "character_count": complexity, "line_count": lines},
            score=raw_score,
            normalized=self._normalize(raw_score),
            metadata={"valid": True, "character_count": complexity, "line_count": lines},
        )


class InstructionEvaluator(BaseEvaluator):
    category = "instruction"

    def evaluate(self) -> EvalResult:
        text = self.response or ""
        expected = (self.prompt.get("expected") or "")
        formatting_score, bullet_count = _bullet_score(text)
        line_count = text.count("\n") + 1
        convenience_score = 1.0 if bullet_count >= 3 else max(0.0, bullet_count / 3)
        constraint_score = _constraint_score(text, expected)
        score = min(1.0, formatting_score * 0.35 + convenience_score * 0.35 + constraint_score * 0.3)

        factors = {
            "word_count": _word_count(text),
            "bullet_count": bullet_count,
            "line_count": line_count,
            "formatting_score": formatting_score,
            "constraint_score": constraint_score,
            "convenience_score": convenience_score,
        }
        return EvalResult(raw={"factors": factors}, score=score, normalized=self._normalize(score), metadata=factors)
