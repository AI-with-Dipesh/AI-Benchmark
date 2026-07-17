from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from aibenchmark.app.history import DB_PATH, _connect


MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS automation_jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        schedule_cron TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        model_filter TEXT,
        benchmarks TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        concurrency INTEGER NOT NULL DEFAULT 1,
        timeout_seconds REAL NOT NULL DEFAULT 120,
        retry_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_run_at TEXT,
        next_run_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_executions (
        execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        trigger TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 1,
        error TEXT,
        results_path TEXT,
        FOREIGN KEY(job_id) REFERENCES automation_jobs(job_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_regressions (
        regression_id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id INTEGER NOT NULL,
        benchmark_name TEXT NOT NULL,
        metric TEXT NOT NULL,
        previous_value REAL NOT NULL,
        current_value REAL NOT NULL,
        delta_pct REAL NOT NULL,
        detected_at TEXT NOT NULL,
        severity TEXT NOT NULL,
        FOREIGN KEY(execution_id) REFERENCES automation_executions(execution_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id INTEGER,
        channel TEXT NOT NULL,
        status TEXT NOT NULL,
        payload TEXT,
        sent_at TEXT NOT NULL,
        error TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_sync_history (
        sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        models_added INTEGER NOT NULL DEFAULT 0,
        models_removed INTEGER NOT NULL DEFAULT 0,
        error TEXT
    )
    """,
]


def migrate(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    owned = False
    if conn is None:
        conn = _connect(DB_PATH)
        owned = True
    try:
        for sql in MIGRATIONS:
            conn.executescript(sql)
        conn.commit()
    finally:
        if owned:
            conn.close()
    return conn

