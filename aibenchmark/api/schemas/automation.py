from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AutomationJobCreate(BaseModel):
    name: str
    schedule_cron: str = "0 * * * *"
    provider_name: str
    model_filter: str | None = None
    benchmarks: str = "coding"
    concurrency: int = 1
    timeout_seconds: float = 120
    retry_count: int = 0


class AutomationJobResponse(BaseModel):
    job_id: int
    name: str
    schedule_cron: str
    provider_name: str
    model_filter: str | None = None
    benchmarks: str
    enabled: bool
    concurrency: int
    timeout_seconds: float
    retry_count: int
    created_at: str
    updated_at: str
    last_run_at: str | None = None
    next_run_at: str | None = None


class AutomationExecutionResponse(BaseModel):
    execution_id: int
    job_id: int
    started_at: str
    finished_at: str | None = None
    status: str
    trigger: str
    attempts: int
    error: str | None = None
    results_path: str | None = None


class RegressionResponse(BaseModel):
    regression_id: int
    execution_id: int
    benchmark_name: str
    metric: str
    previous_value: float
    current_value: float
    delta_pct: float
    detected_at: str
    severity: str


class NotificationResponse(BaseModel):
    notification_id: int
    execution_id: int | None = None
    channel: str
    status: str
    sent_at: str
    error: str | None = None


class SyncHistoryResponse(BaseModel):
    sync_id: int
    provider_name: str
    started_at: str
    finished_at: str | None = None
    status: str
    models_added: int = 0
    models_removed: int = 0
    error: str | None = None


class AutoTestNotificationRequest(BaseModel):
    channel: str
    subject: str = "Test Notification"
    body: str = "This is a test notification from AI-Benchmark automation."

