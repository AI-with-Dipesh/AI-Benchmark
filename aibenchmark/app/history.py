from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


DB_PATH = Path.home() / ".local" / "share" / "aibenchmark" / "history.db"


@dataclass(frozen=True)
class RunSummary:
    run_id: int
    timestamp: datetime
    provider: str
    model: str
    overall: float
    benchmark_count: int


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    owned = False
    if conn is None:
        conn = _connect()
        owned = True
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            overall REAL NOT NULL,
            benchmark_count INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_scores (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            benchmark TEXT NOT NULL,
            raw REAL NOT NULL,
            normalized REAL NOT NULL,
            weight REAL NOT NULL,
            weighted REAL NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs (run_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_details (
            run_id INTEGER PRIMARY KEY,
            details TEXT,
            metadata TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (run_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(timestamp)"
    )
    if owned:
        conn.commit()
    return conn


def save_run(results: list[BenchmarkResult], details: dict[str, Any] | None = None, db_path: Path | None = None, conn: sqlite3.Connection | None = None) -> int:
    if not results:
        raise ValueError("Cannot save empty results.")
    owned = False
    if conn is None:
        conn = _connect(db_path)
        owned = True
    init_db(conn)
    now = datetime.now(timezone.utc).isoformat()
    primary = results[0]
    cur = conn.execute(
        "INSERT INTO runs (timestamp, provider, model, overall, benchmark_count) VALUES (?, ?, ?, ?, ?)",
        (now, primary.provider.value, primary.model, primary.overall, len(results)),
    )
    run_id = int(cur.lastrowid)
    for r in results:
        for s in r.scores:
            conn.execute(
                "INSERT INTO benchmark_scores (run_id, benchmark, raw, normalized, weight, weighted) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    s.benchmark.value,
                    float(s.raw),
                    float(s.normalized),
                    float(s.weight),
                    float(s.weighted),
                ),
            )
    if details:
        conn.execute(
            "INSERT INTO run_details (run_id, details, metadata) VALUES (?, ?, ?)",
            (run_id, json.dumps(details, default=_json_default), None),
        )
    if owned:
        conn.commit()
        conn.close()
    return run_id


def load_latest(n: int = 1, db_path: Path | None = None) -> list[list[BenchmarkResult]]:
    conn = _connect(db_path)
    init_db(conn)
    rows = conn.execute(
        "SELECT run_id FROM runs ORDER BY timestamp DESC LIMIT ?", (n,)
    ).fetchall()
    return [load_run(int(row["run_id"]), db_path=db_path, conn=conn) for row in rows]


def load_run(run_id: int, db_path: Path | None = None, conn: sqlite3.Connection | None = None) -> list[BenchmarkResult]:
    owned = False
    if conn is None:
        conn = _connect(db_path)
        owned = True
    init_db(conn)
    run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if not run:
        raise KeyError(f"Run {run_id} not found.")
    scores = conn.execute(
        "SELECT benchmark, raw, normalized, weight, weighted FROM benchmark_scores WHERE run_id = ?",
        (run_id,),
    ).fetchall()
    results: dict[tuple[str, str], BenchmarkResult] = {}
    for s in scores:
        key = (run["provider"], run["model"])
        if key not in results:
            results[key] = BenchmarkResult(
                model=run["model"],
                provider=ProviderType(run["provider"]),
                metadata={"timestamp": run["timestamp"]},
            )
        try:
            benchmark = BenchmarkName(s["benchmark"])
        except ValueError:
            continue
        results[key].scores.append(
            Score(
                benchmark=benchmark,
                raw=s["raw"],
                normalized=s["normalized"],
                weight=s["weight"],
                weighted=s["weighted"],
            )
        )
    for r in results.values():
        r.calculate_overall()
    return list(results.values())


def _json_default(value: Any) -> Any:
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, (datetime, )):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
