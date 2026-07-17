from __future__ import annotations

import click

from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import AutomationJob


@click.group()
def automation() -> None:
    """Automation commands."""
    pass


@automation.command("create")
@click.option("--name", required=True)
@click.option("--schedule", default="0 * * * *", show_default=True)
@click.option("--provider", required=True)
@click.option("--model-filter", default=None)
@click.option("--benchmarks", default="coding", show_default=True)
@click.option("--concurrency", default=1, type=int)
@click.option("--timeout", default=120, type=float)
@click.option("--retry", default=0, type=int)
def automation_create(name: str, schedule: str, provider: str, model_filter: str | None, benchmarks: str, concurrency: int, timeout: float, retry: int) -> None:
    manager = AutomationManager()
    job = manager.create_job(AutomationJob(
        name=name,
        schedule_cron=schedule,
        provider_name=provider,
        model_filter=model_filter,
        benchmarks=benchmarks,
        concurrency=concurrency,
        timeout_seconds=timeout,
        retry_count=retry,
    ))
    click.echo(f"Created job {job.job_id}: {job.name}")


@automation.command("list")
def automation_list() -> None:
    manager = AutomationManager()
    jobs = manager.list_jobs()
    for job in jobs:
        click.echo(f"{job['job_id']}: {job['name']} [{job['schedule_cron']}] enabled={job['enabled']}")


@automation.command("run")
@click.argument("job_id", type=int)
def automation_run(job_id: int) -> None:
    from aibenchmark.app.automation.scheduler import BenchmarkScheduler
    manager = AutomationManager()
    scheduler = BenchmarkScheduler(manager)
    job_data = manager.get_job(job_id)
    if job_data is None:
        raise click.ClickException("Job not found")
    job = AutomationJob(**job_data)
    execution = scheduler.run_job(job)
    click.echo(f"Started execution {execution.execution_id} for job {job_id}")


@automation.command("delete")
@click.argument("job_id", type=int)
def automation_delete(job_id: int) -> None:
    manager = AutomationManager()
    manager.delete_job(job_id)
    click.echo(f"Deleted job {job_id}")


@automation.command("history")
@click.option("--job-id", type=int, default=None)
def automation_history(job_id: int | None) -> None:
    manager = AutomationManager()
    executions = manager.list_executions(job_id)
    for ex in executions:
        click.echo(f"{ex['execution_id']}: job={ex['job_id']} status={ex['status']} trigger={ex['trigger']}")


@automation.command("notifications")
def automation_notifications() -> None:
    manager = AutomationManager()
    notifications = manager.list_notifications()
    for n in notifications:
        click.echo(f"{n['notification_id']}: {n['channel']} {n['status']} error={n['error']}")


@automation.command("regressions")
def automation_regressions() -> None:
    manager = AutomationManager()
    regressions = manager.list_regressions()
    for r in regressions:
        click.echo(f"{r['regression_id']}: {r['benchmark_name']} {r['metric']} delta={r['delta_pct']:.2f}% severity={r['severity']}")

