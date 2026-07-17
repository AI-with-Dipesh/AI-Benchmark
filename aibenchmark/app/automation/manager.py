from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from aibenchmark.app.automation.models import (
    AutomationExecution,
    AutomationJob,
    ExecutionStatus,
    JobStatus,
    NotificationRecord,
    RegressionRecord,
    SyncRecord,
    TriggerType,
)
from aibenchmark.app.automation.migration import migrate

logger = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".local" / "share" / "aibenchmark" / "automation.db"
if "PYTEST_CURRENT_TEST" in __import__("os").environ:
    _DB_PATH = Path("/tmp/aibenchmark_automation_test.db")
_lock = threading.Lock()


class AutomationManager:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._initialize()

    def _initialize(self) -> None:
        with self._connection() as conn:
            migrate(conn)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Jobs
    def create_job(self, job: AutomationJob) -> AutomationJob:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_jobs (name, schedule_cron, provider_name, model_filter, benchmarks, enabled, concurrency, timeout_seconds, retry_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.name,
                    job.schedule_cron,
                    job.provider_name,
                    job.model_filter,
                    job.benchmarks,
                    1 if job.enabled else 0,
                    job.concurrency,
                    job.timeout_seconds,
                    job.retry_count,
                    job.created_at,
                    job.updated_at,
                ),
            )
            job_id = cur.lastrowid
        return AutomationJob(
            job_id=job_id,
            name=job.name,
            schedule_cron=job.schedule_cron,
            provider_name=job.provider_name,
            model_filter=job.model_filter,
            benchmarks=job.benchmarks,
            enabled=job.enabled,
            concurrency=job.concurrency,
            timeout_seconds=job.timeout_seconds,
            retry_count=job.retry_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            last_run_at=job.last_run_at,
            next_run_at=job.next_run_at,
        )

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM automation_jobs ORDER BY job_id DESC").fetchall()
            return [dict(row) for row in rows]

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM automation_jobs WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def update_job(self, job_id: int, **kwargs: Any) -> None:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [datetime.now(timezone.utc).isoformat(), job_id]
        with self._connection() as conn:
            conn.execute(f"UPDATE automation_jobs SET {set_clause}, updated_at = ? WHERE job_id = ?", values)

    def delete_job(self, job_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM automation_executions WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM automation_jobs WHERE job_id = ?", (job_id,))

    # Executions
    def create_execution(self, execution: AutomationExecution) -> AutomationExecution:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_executions (job_id, started_at, finished_at, status, trigger, attempts, error, results_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.job_id,
                    execution.started_at,
                    execution.finished_at,
                    execution.status,
                    execution.trigger,
                    execution.attempts,
                    execution.error,
                    execution.results_path,
                ),
            )
            execution_id = cur.lastrowid
        return AutomationExecution(
            execution_id=execution_id,
            job_id=execution.job_id,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            status=execution.status,
            trigger=execution.trigger,
            attempts=execution.attempts,
            error=execution.error,
            results_path=execution.results_path,
        )

    def update_execution(self, execution_id: int, **kwargs: Any) -> None:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [execution_id]
        with self._connection() as conn:
            conn.execute(f"UPDATE automation_executions SET {set_clause} WHERE execution_id = ?", values)

    def list_executions(self, job_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM automation_executions"
        params: list[Any] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            params.append(job_id)
        query += " ORDER BY execution_id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # Regressions
    def record_regression(self, regression: RegressionRecord) -> RegressionRecord:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_regressions (execution_id, benchmark_name, metric, previous_value, current_value, delta_pct, detected_at, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    regression.execution_id,
                    regression.benchmark_name,
                    regression.metric,
                    regression.previous_value,
                    regression.current_value,
                    regression.delta_pct,
                    regression.detected_at,
                    regression.severity,
                ),
            )
            regression_id = cur.lastrowid
        return RegressionRecord(
            regression_id=regression_id,
            execution_id=regression.execution_id,
            benchmark_name=regression.benchmark_name,
            metric=regression.metric,
            previous_value=regression.previous_value,
            current_value=regression.current_value,
            delta_pct=regression.delta_pct,
            detected_at=regression.detected_at,
            severity=regression.severity,
        )

    def list_regressions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM automation_regressions ORDER BY regression_id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    # Notifications
    def record_notification(self, notification: NotificationRecord) -> NotificationRecord:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_notifications (execution_id, channel, status, payload, sent_at, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.execution_id,
                    notification.channel,
                    notification.status,
                    notification.payload,
                    notification.sent_at,
                    notification.error,
                ),
            )
            notification_id = cur.lastrowid
        return NotificationRecord(
            notification_id=notification_id,
            execution_id=notification.execution_id,
            channel=notification.channel,
            status=notification.status,
            payload=notification.payload,
            sent_at=notification.sent_at,
            error=notification.error,
        )

    def list_notifications(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM automation_notifications ORDER BY notification_id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    # Sync history
    def record_sync(self, sync: SyncRecord) -> SyncRecord:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_sync_history (provider_name, started_at, finished_at, status, models_added, models_removed, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync.provider_name,
                    sync.started_at,
                    sync.finished_at,
                    sync.status,
                    sync.models_added,
                    sync.models_removed,
                    sync.error,
                ),
            )
            sync_id = cur.lastrowid
        return SyncRecord(
            sync_id=sync_id,
            provider_name=sync.provider_name,
            started_at=sync.started_at,
            finished_at=sync.finished_at,
            status=sync.status,
            models_added=sync.models_added,
            models_removed=sync.models_removed,
            error=sync.error,
        )

    def list_sync_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM automation_sync_history ORDER BY sync_id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

