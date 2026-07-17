from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from aibenchmark.api.app import create_app
from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import AutomationJob, AutomationExecution, ExecutionStatus, NotificationRecord, RegressionRecord, SyncRecord
from aibenchmark.app.automation.regression import RegressionDetector
from aibenchmark.app.automation.notifications import (
    ConsoleNotificationProvider,
    DiscordNotificationProvider,
    EmailNotificationProvider,
    NotificationService,
    SlackNotificationProvider,
    WebhookNotificationProvider,
)
from aibenchmark.app.automation.sync import ModelSyncService
from aibenchmark.app.history import _connect as history_connect

TEST_DB = Path("/tmp/aibenchmark_automation_test.db")


@pytest.fixture(autouse=True)
def isolated_manager(tmp_path):
    db_path = tmp_path / "automation.db"
    manager = AutomationManager(db_path=db_path)
    yield manager
    # cleanup handled by tmp_path


class TestAutomationManager:
    def test_create_and_list_jobs(self, isolated_manager):
        job = isolated_manager.create_job(AutomationJob(
            name="test-job",
            schedule_cron="*/5 * * * *",
            provider_name="openrouter",
            benchmarks="coding",
        ))
        assert job.job_id is not None
        jobs = isolated_manager.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test-job"

    def test_update_and_delete_job(self, isolated_manager):
        job = isolated_manager.create_job(AutomationJob(name="to-delete", schedule_cron="0 0 * * *", provider_name="openrouter", benchmarks="coding"))
        isolated_manager.update_job(job.job_id, enabled=False)
        updated = isolated_manager.get_job(job.job_id)
        assert updated["enabled"] == 0
        isolated_manager.delete_job(job.job_id)
        assert isolated_manager.get_job(job.job_id) is None

    def test_executions(self, isolated_manager):
        job = isolated_manager.create_job(AutomationJob(name="exec-test", schedule_cron="* * * * *", provider_name="openrouter", benchmarks="coding"))
        ex = isolated_manager.create_execution(AutomationExecution(job_id=job.job_id or 0))
        assert ex.execution_id is not None
        isolated_manager.update_execution(ex.execution_id, status=ExecutionStatus.SUCCESS.value)
        executions = isolated_manager.list_executions(job.job_id)
        assert executions[0]["status"] == ExecutionStatus.SUCCESS.value

    def test_regressions(self, isolated_manager):
        job = isolated_manager.create_job(AutomationJob(name="reg-test", schedule_cron="* * * * *", provider_name="openrouter", benchmarks="coding"))
        ex = isolated_manager.create_execution(AutomationExecution(job_id=job.job_id or 0, status=ExecutionStatus.SUCCESS.value))
        reg = isolated_manager.record_regression(RegressionRecord(execution_id=ex.execution_id or 0, benchmark_name="coding", metric="overall", previous_value=1.0, current_value=0.8, delta_pct=-20.0))
        assert reg.regression_id is not None
        regs = isolated_manager.list_regressions()
        assert len(regs) == 1
        assert regs[0]["delta_pct"] == -20.0

    def test_notifications(self, isolated_manager):
        n = isolated_manager.record_notification(NotificationRecord(channel="console", status="sent"))
        assert n.notification_id is not None
        notes = isolated_manager.list_notifications()
        assert len(notes) == 1

    def test_sync_history(self, isolated_manager):
        s = isolated_manager.record_sync(SyncRecord(provider_name="openrouter", status="success", models_added=2, models_removed=0))
        assert s.sync_id is not None
        syncs = isolated_manager.list_sync_history()
        assert len(syncs) == 1


class TestRegressionDetector:
    def test_detects_decline(self, tmp_path):
        from aibenchmark.app.history import init_db, _connect as history_connect
        history_db_path = tmp_path / "history.db"
        conn = init_db(history_connect(history_db_path))
        automation_db_path = tmp_path / "automation.db"
        from aibenchmark.app.automation.manager import AutomationManager
        from aibenchmark.app.automation.regression import RegressionDetector
        manager = AutomationManager(db_path=automation_db_path)
        detector = RegressionDetector(manager=manager, threshold_pct=10.0, history_db_path=history_db_path)
        conn.execute("INSERT INTO runs (timestamp, provider, model, overall, benchmark_count) VALUES (?, ?, ?, ?, ?)",
                     ("2026-01-01T00:00:00Z", "openrouter", "m1", 1.0, 1))
        conn.execute("INSERT INTO benchmark_scores (run_id, benchmark, raw, normalized, weight, weighted) VALUES (?, ?, ?, ?, ?, ?)",
                     (1, "coding", 0.0, 1.0, 1.0, 1.0))
        conn.execute("INSERT INTO runs (timestamp, provider, model, overall, benchmark_count) VALUES (?, ?, ?, ?, ?)",
                     ("2026-01-02T00:00:00Z", "openrouter", "m1", 0.9, 1))
        conn.execute("INSERT INTO benchmark_scores (run_id, benchmark, raw, normalized, weight, weighted) VALUES (?, ?, ?, ?, ?, ?)",
                     (2, "coding", 0.0, 0.9, 1.0, 0.9))
        conn.commit()
        from aibenchmark.app.models import BenchmarkResult, ProviderType, Score, BenchmarkName
        current = [BenchmarkResult(model="m1", provider=ProviderType.OPENROUTER, scores=[Score(benchmark=BenchmarkName.CODING, raw=0.0, normalized=0.8, weight=1.0, weighted=0.8)], overall=0.8)]
        regressions = detector.detect(1, current)
        assert len(regressions) == 1
        assert abs(regressions[0].delta_pct - -20.0) < 0.01


class TestNotificationProviders:
    def test_console(self):
        svc = NotificationService()
        provider = ConsoleNotificationProvider()
        svc.register("console", provider)
        svc.send("console", "test-subject", "test-body", execution_id=1)
        # Just verify no exception is raised; console logs don't need caplog

    def test_webhook_failure(self):
        svc = NotificationService()
        svc.register("webhook", WebhookNotificationProvider("http://127.0.0.1:1/"))
        # should log error, not raise
        svc.send("webhook", "subj", "body", execution_id=1)

    def test_slack_failure(self):
        svc = NotificationService()
        svc.register("slack", SlackNotificationProvider("http://127.0.0.1:1/"))
        svc.send("slack", "subj", "body", execution_id=1)

    def test_discord_failure(self):
        svc = NotificationService()
        svc.register("discord", DiscordNotificationProvider("http://127.0.0.1/"))
        svc.send("discord", "subj", "body", execution_id=1)


class TestAPIEndpoints:
    @pytest.fixture(scope="session")
    def client(self):
        app = create_app()
        from fastapi.testclient import TestClient
        return TestClient(app, raise_server_exceptions=False)

    def test_list_jobs(self, client):
        r = client.get("/api/v1/automation/jobs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_job(self, client):
        r = client.post("/api/v1/automation/jobs", json={
            "name": "api-job",
            "schedule_cron": "0 * * * *",
            "provider_name": "openrouter",
            "benchmarks": "coding,latency",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "api-job"

    def test_run_job_and_get_id(self, client):
        r = client.post("/api/v1/automation/jobs", json={
            "name": "run-job",
            "schedule_cron": "0 0 * * *",
            "provider_name": "openrouter",
            "benchmarks": "coding",
        })
        job_id = r.json()["job_id"]
        r2 = client.post(f"/api/v1/automation/jobs/{job_id}/run")
        assert r2.status_code == 200

    def test_automation_history(self, client):
        r = client.get("/api/v1/automation/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_regressions_and_notifications(self, client):
        assert client.get("/api/v1/automation/regressions").status_code == 200
        assert client.get("/api/v1/automation/notifications").status_code == 200

    def test_test_notification(self, client):
        r = client.post("/api/v1/automation/test-notification", json={"channel": "console"})
        assert r.status_code == 200

    def test_delete_job(self, client):
        r = client.post("/api/v1/automation/jobs", json={
            "name": "delete-me",
            "schedule_cron": "* * * * *",
            "provider_name": "openrouter",
            "benchmarks": "coding",
        })
        job_id = r.json()["job_id"]
        assert client.delete(f"/api/v1/automation/jobs/{job_id}").status_code == 204
        jobs = client.get("/api/v1/automation/jobs").json()
        assert not any(j.get("job_id") == job_id for j in jobs)

