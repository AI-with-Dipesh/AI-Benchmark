from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.automation import (
    AutoTestNotificationRequest,
    AutomationExecutionResponse,
    AutomationJobCreate,
    AutomationJobResponse,
    NotificationResponse,
    RegressionResponse,
    SyncHistoryResponse,
)
from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import TriggerType
from aibenchmark.app.automation.notifications import NotificationService
from aibenchmark.app.automation.regression import RegressionDetector
from aibenchmark.app.automation.scheduler import BenchmarkScheduler
from aibenchmark.app.automation.sync import ModelSyncService

router = APIRouter(prefix="/automation", tags=["automation"])


def get_manager() -> AutomationManager:
    return AutomationManager()


def get_scheduler() -> BenchmarkScheduler:
    return BenchmarkScheduler()


def get_notifier() -> NotificationService:
    service = NotificationService()
    service.register("console", __import__("aibenchmark.app.automation.notifications", fromlist=["ConsoleNotificationProvider"]).ConsoleNotificationProvider())
    return service


@router.get("/jobs", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
def list_jobs(manager: AutomationManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return manager.list_jobs()


@router.post("/jobs", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_job(body: AutomationJobCreate, manager: AutomationManager = Depends(get_manager)) -> dict[str, Any]:
    from aibenchmark.app.automation.models import AutomationJob as AJ
    job = manager.create_job(AJ(
        name=body.name,
        schedule_cron=body.schedule_cron,
        provider_name=body.provider_name,
        model_filter=body.model_filter,
        benchmarks=body.benchmarks,
        concurrency=body.concurrency,
        timeout_seconds=body.timeout_seconds,
        retry_count=body.retry_count,
    ))
    return dict(job.__dict__)


@router.patch("/jobs/{job_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def update_job(job_id: int, body: dict[str, Any], manager: AutomationManager = Depends(get_manager)) -> dict[str, Any]:
    manager.update_job(job_id, **body)
    job = manager.get_job(job_id)
    return job or {}


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, manager: AutomationManager = Depends(get_manager)) -> None:
    manager.delete_job(job_id)


@router.post("/jobs/{job_id}/run", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def run_job(job_id: int, scheduler: BenchmarkScheduler = Depends(get_scheduler), manager: AutomationManager = Depends(get_manager)) -> dict[str, Any]:
    job_data = manager.get_job(job_id)
    if job_data is None:
        return {"error": "Job not found"}
    from aibenchmark.app.automation.models import AutomationJob as AJ
    job = AJ(**job_data)
    execution = scheduler.run_job(job)
    return dict(execution.__dict__)


@router.get("/history", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
def automation_history(manager: AutomationManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return manager.list_executions()


@router.get("/regressions", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
def list_regressions(manager: AutomationManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return manager.list_regressions()


@router.get("/notifications", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
def list_notifications(manager: AutomationManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return manager.list_notifications()


@router.post("/test-notification", status_code=status.HTTP_200_OK)
def test_notification(body: AutoTestNotificationRequest, notifier: NotificationService = Depends(get_notifier)) -> dict[str, Any]:
    notifier.send(body.channel, body.subject, body.body, payload={"test": True})
    return {"status": "queued", "channel": body.channel}

