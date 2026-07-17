from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    ENABLED = "enabled"
    PAUSED = "paused"
    RUNNING = "running"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    RETRY = "retry"
    WEBHOOK = "webhook"


@dataclass(frozen=True)
class AutomationJob:
    job_id: int | None = None
    name: str = ""
    schedule_cron: str = ""
    provider_name: str = ""
    model_filter: str | None = None
    benchmarks: str = ""
    enabled: bool = True
    concurrency: int = 1
    timeout_seconds: float = 120.0
    retry_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run_at: str | None = None
    next_run_at: str | None = None


@dataclass(frozen=True)
class AutomationExecution:
    execution_id: int | None = None
    job_id: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    status: str = ExecutionStatus.PENDING.value
    trigger: str = TriggerType.MANUAL.value
    attempts: int = 1
    error: str | None = None
    results_path: str | None = None


@dataclass(frozen=True)
class RegressionRecord:
    regression_id: int | None = None
    execution_id: int = 0
    benchmark_name: str = ""
    metric: str = ""
    previous_value: float = 0.0
    current_value: float = 0.0
    delta_pct: float = 0.0
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    severity: str = "medium"


@dataclass(frozen=True)
class NotificationRecord:
    notification_id: int | None = None
    execution_id: int | None = None
    channel: str = ""
    status: str = ""
    payload: str | None = None
    sent_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None


@dataclass(frozen=True)
class SyncRecord:
    sync_id: int | None = None
    provider_name: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    status: str = ExecutionStatus.PENDING.value
    models_added: int = 0
    models_removed: int = 0
    error: str | None = None

