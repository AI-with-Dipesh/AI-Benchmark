from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import AutomationJob, AutomationExecution, ExecutionStatus, TriggerType
from aibenchmark.app.engine import BenchEngine

logger = logging.getLogger(__name__)


class BenchmarkScheduler:
    def __init__(self, manager: AutomationManager | None = None) -> None:
        self.manager = manager or AutomationManager()
        self._engine: BenchEngine | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def _get_engine(self) -> BenchEngine:
        if self._engine is None:
            self._engine = BenchEngine()
        return self._engine

    def submit(self, job: AutomationJob, trigger: TriggerType = TriggerType.MANUAL) -> AutomationExecution:
        execution = self.manager.create_execution(
            AutomationExecution(
                job_id=job.job_id or 0,
                status=ExecutionStatus.PENDING.value,
                trigger=trigger.value,
                attempts=1,
            )
        )
        return execution

    def run_job(self, job: AutomationJob) -> AutomationExecution:
        execution = self.submit(job, TriggerType.SCHEDULED)
        self._execute(execution, job)
        return execution

    def _execute(self, execution: AutomationExecution, job: AutomationJob) -> None:
        self.manager.update_execution(execution.execution_id, status=ExecutionStatus.RUNNING.value)
        try:
            engine = self._get_engine()
            benchmarks = job.benchmarks.split(",") if job.benchmarks else []
            results = []
            for benchmark_name in benchmarks:
                try:
                    result = engine.run_benchmark(
                        job.provider_name,
                        job.model_filter or "",
                        benchmark_name.strip(),
                        [{"role": "user", "content": "automated benchmark"}],
                    )
                    results.append(result)
                except Exception as exc:
                    logger.debug("Scheduled benchmark '%s' failed: %s", benchmark_name, exc)
            from aibenchmark.app.history import save_run
            from pathlib import Path
            out_dir = Path("automation_runs") / str(job.job_id)
            try:
                save_run(results, details={"source": "automation", "job_id": job.job_id}, db_path=out_dir / "history.db")
            except Exception:
                pass
            self.manager.update_execution(
                execution.execution_id,
                status=ExecutionStatus.SUCCESS.value,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            job_data = {
                "job_id": job.job_id,
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "next_run_at": None,
            }
            self.manager.update_job(job.job_id, **job_data)
        except Exception as exc:
            logger.error("Scheduled job '%s' failed: %s", job.name, exc)
            self.manager.update_execution(
                execution.execution_id,
                status=ExecutionStatus.FAILED.value,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=str(exc),
            )

