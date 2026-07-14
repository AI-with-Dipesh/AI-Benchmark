from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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


# Sprint 5: Universal Provider Platform models


@dataclass(frozen=True)
class ProviderCapabilities:
    chat: bool = True
    reasoning: bool = False
    vision: bool = False
    streaming: bool = False
    function_calling: bool = False
    json_mode: bool = False
    structured_output: bool = False
    embeddings: bool = False
    image_generation: bool = False
    audio: bool = False
    tool_calling: bool = False
    long_context: bool = False
    context_window: int | None = None
    max_output_tokens: int | None = None

    def has(self, capability: str) -> bool:
        return getattr(self, capability, False)

    def flags(self) -> list[str]:
        return [k for k, v in self.__dict__.items() if isinstance(v, bool) and v]


@dataclass(frozen=True)
class ProviderMetadata:
    provider_name: str
    provider_version: str | None = None
    endpoint: str | None = None
    region: str | None = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    supported_models: list[str] = field(default_factory=list)
    authentication_type: str = "api_key"
    pricing: dict[str, Any] = field(default_factory=dict)
    token_limits: dict[str, int | None] = field(default_factory=dict)
    context_window: int | None = None
    streaming_support: bool = False
    function_calling_support: bool = False
    vision_support: bool = False
    reasoning_support: bool = False
    embeddings_support: bool = False
    json_mode_support: bool = False


@dataclass(frozen=True)
class RateLimitStatus:
    remaining: int | None = None
    limit: int | None = None
    reset_seconds: int | None = None
    retry_after: int | None = None
    is_rate_limited: bool = False
    quota_exceeded: bool = False
    provider_maintenance: bool = False
    daily_quota_exceeded: bool = False
    burst_limit_hit: bool = False
    provider_specific_limits: dict[str, Any] = field(default_factory=dict)

    @property
    def retry_recommendation(self) -> str:
        if self.provider_maintenance:
            return "Provider is under maintenance. Retry later."
        if self.quota_exceeded or self.daily_quota_exceeded:
            return "Quota exceeded. Wait until next billing cycle or upgrade plan."
        if self.burst_limit_hit:
            return "Burst limit hit. Reduce request rate."
        if self.is_rate_limited:
            if self.retry_after:
                return f"Rate limited. Retry after {self.retry_after} seconds."
            return "Rate limited. Reduce request frequency."
        return "No rate limit detected."


@dataclass(frozen=True)
class AuthResult:
    authenticated: bool
    provider: str
    message: str = ""
    credential_valid: bool = False
    expires_at: str | None = None
    scopes: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderPluginConfig:
    name: str
    enabled: bool = True
    priority: int = 100
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    api_key_env: str = ""
    base_url: str = ""
    timeout_seconds: float = 60.0
    max_retries: int = 3
    backoff_factor: float = 1.5


class ProviderStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderHealth:
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    availability: float = 0.0
    authentication_status: bool = False
    connection_health: bool = True
    average_latency_ms: float | None = None
    median_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    p99_latency_ms: float | None = None
    failure_rate: float = 0.0
    timeout_rate: float = 0.0
    retry_rate: float = 0.0
    total_checks: int = 0
    last_check: str = ""
    rate_limit: RateLimitStatus = field(default_factory=RateLimitStatus)


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


# Sprint 6: intelligent routing models
@dataclass(frozen=True)
class ExecutionPolicy:
    retry_count: int = 2
    backoff_factor: float = 1.5
    fallback_enabled: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    circuit_breaker_threshold: float = 0.5
    circuit_breaker_cooldown_seconds: int = 300


@dataclass(frozen=True)
class RoutingContext:
    benchmark_name: BenchmarkName
    provider_name: str | None = None
    model: str | None = None
    max_cost: float | None = None
    required_capabilities: list[str] = field(default_factory=list)
    prefer_free: bool = False
    min_capability_score: float = 0.7
    history_runs: int = 5


@dataclass(frozen=True)
class RoutingPlan:
    provider: str
    model: str
    estimated_cost: float | None = None
    rationale: str = ""
    fallback_providers: list[str] = field(default_factory=list)
    fallback_models: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CostReport:
    total_cost: float
    entries: list[CostEntry]
    by_provider: dict[str, float]
    by_model: dict[str, float]
