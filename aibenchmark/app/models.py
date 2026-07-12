from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

    def calculate_overall(self) -> float:
        total_weight = sum(s.weight for s in self.scores) or 1
        self.overall = sum(s.weighted for s in self.scores) / total_weight
        return self.overall
