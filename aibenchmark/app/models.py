from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class BenchmarkName(str, Enum):
    LATENCY = "latency"
    CODING = "coding"
    DEBUGGING = "debugging"
    REASONING = "reasoning"
    RESEARCH = "research"
    JSON = "json"
    CONTEXT = "context"
    TOOL_CALLING = "tool_calling"
    RELIABILITY = "reliability"
    GENERAL = "general"
    CODE_REVIEW = "code_review"
    INSTRUCTION = "instruction"


class PluginCategory(str, Enum):
    PROVIDER = "provider"
    BENCHMARK = "benchmark"
    EVALUATOR = "evaluator"
    REPORTER = "reporter"
    STRATEGY = "strategy"


class ResponseObject(BaseModel):
    provider: ProviderType
    model: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


@dataclass
class Score:
    benchmark: BenchmarkName
    raw: float
    normalized: float = 0.0
    weight: float = 1.0
    weighted: float = 0.0

    def __post_init__(self) -> None:
        self.weighted = self.normalized * self.weight


@dataclass
class BenchmarkResult:
    model: str
    provider: ProviderType
    scores: list[Score] = field(default_factory=list)
    overall: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Sprint 4: reproducibility & metadata
    model_version: str | None = None
    prompt_version: str | None = None
    benchmark_version: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    seed: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    retry_count: int = 0
    timeout_status: str | None = None
    evaluation: str | None = None
    objective_validation: float | None = None
    confidence: float | None = None

    def calculate_overall(self) -> float:
        total_weight = sum(s.weight for s in self.scores) or 1
        self.overall = sum(s.weighted for s in self.scores) / total_weight
        return self.overall


# Sprint 4 domain dataclasses
@dataclass(frozen=True)
class RetryPolicy:
    retry_count: int = 3
    backoff_factor: float = 1.5
    retryable: tuple[str, ...] = ("timeout", "connection", "rate", "server_error")


@dataclass(frozen=True)
class TimeoutPolicy:
    request_timeout_seconds: float = 60.0
    benchmark_timeout_seconds: float = 120.0
    category_timeout_seconds: float = 60.0
    connect_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def tokens_per_second(self) -> float | None:
        # latency_seconds must be supplied externally if needed
        return None


@dataclass(frozen=True)
class CostEntry:
    provider: str
    model: str
    prompt_price_per_1k: float
    completion_price_per_1k: float
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def estimated_cost(self) -> float:
        return (self.prompt_tokens / 1000.0) * self.prompt_price_per_1k + (
            self.completion_tokens / 1000.0
        ) * self.completion_price_per_1k


@dataclass(frozen=True)
class ReliabilityEntry:
    provider: str
    model: str
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    retry_count: int = 0
    total_latency_ms: float = 0.0
    latency_samples: tuple[float, ...] = ()

    @property
    def total_attempts(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        attempts = self.total_attempts
        return self.success_count / attempts if attempts else 0.0

    @property
    def failure_rate(self) -> float:
        attempts = self.total_attempts
        return self.failure_count / attempts if attempts else 0.0

    @property
    def timeout_rate(self) -> float:
        attempts = self.total_attempts
        return self.timeout_count / attempts if attempts else 0.0

    @property
    def average_latency_ms(self) -> float | None:
        count = self.success_count
        return self.total_latency_ms / count if count else None

    @property
    def p95_latency_ms(self) -> float | None:
        if not self.latency_samples:
            return None
        return _percentile(self.latency_samples, 95)

    @property
    def p99_latency_ms(self) -> float | None:
        if not self.latency_samples:
            return None
        return _percentile(self.latency_samples, 99)

    def add_latency(self, latency_ms: float) -> None:
        # mutable factory pattern; frozen dataclass cannot mutate, so this
        # becomes a generator helper outside the dataclass.
        pass


def _percentile(samples: tuple[float, ...], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    k = (len(ordered) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(ordered):
        return float(ordered[f])
    return float(ordered[f] + (ordered[c] - ordered[f]) * (k - f))


@dataclass(frozen=True)
class StatisticSummary:
    mean: float
    median: float
    variance: float
    std_dev: float
    confidence_interval_95: tuple[float, float]
    coefficient_of_variation: float
    sample_count: int

    @classmethod
    def from_values(cls, values: list[float]) -> StatisticSummary:
        if not values:
            return cls(0.0, 0.0, 0.0, 0.0, (0.0, 0.0), 0.0, 0)
        n = len(values)
        mean = sum(values) / n
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        variance = sum((x - mean) ** 2 for x in values) / n if n else 0.0
        std_dev = variance ** 0.5
        cr = 1.96 * (std_dev / (n ** 0.5)) if n else 0.0
        ci = (mean - cr, mean + cr)
        cv = (std_dev / mean) if mean else 0.0
        return cls(
            mean=mean,
            median=median,
            variance=variance,
            std_dev=std_dev,
            confidence_interval_95=ci,
            coefficient_of_variation=cv,
            sample_count=n,
        )


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "critical", "major", "minor", "enhancement"
    category: str
    message: str
    detail: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    issues: list[ValidationIssue]

    def summary(self) -> str:
        lines = [f"Validation: {'PASS' if self.valid else 'FAIL'}"]
        for issue in self.issues:
            lines.append(f"- [{issue.severity}] {issue.category}: {issue.message}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CalibrationReport:
    category_bias: dict[str, float]
    inflation_factor: float
    discriminative_power: dict[str, float]
    recommendation_instability: float
    issues: list[ValidationIssue]


@dataclass(frozen=True)
class RecommendationStability:
    stable: bool
    flip_count: int
    confidence_spread: float
    issues: list[ValidationIssue]


@dataclass(frozen=True)
class ReliabilityReport:
    entries: dict[str, ReliabilityEntry]
    provider_availability: dict[str, float]


@dataclass(frozen=True)
class TokenReport:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    tokens_per_second: float | None
    provider_model_breakdown: dict[str, TokenUsage]


@dataclass(frozen=True)
class CostReport:
    total_cost: float
    entries: list[CostEntry]
    by_provider: dict[str, float]
    by_model: dict[str, float]
