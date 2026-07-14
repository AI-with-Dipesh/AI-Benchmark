from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    conn = sqlite3.connect(path, check_same_thread=False)
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


class HistoryWriter:
    _instance: HistoryWriter | None = None
    _init_lock = threading.Lock()

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self._conn = _connect(self.db_path)
        self._lock = threading.Lock()
        init_db(self._conn)

    @classmethod
    def instance(cls, db_path: Path | None = None) -> HistoryWriter:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._init_lock:
            if cls._instance is not None and cls._instance._conn is not None:
                try:
                    cls._instance._conn.close()
                except Exception:
                    pass
            cls._instance = None

    def save_run(self, results: list[BenchmarkResult], details: dict[str, Any] | None = None) -> int:
        with self._lock:
            return save_run(results, details=details, db_path=self.db_path, conn=self._conn)


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
        metadata_json = {}
        for r in results:
            key = f"{r.provider.value}:{r.model}"
            entry = {
                "metadata": r.metadata,
                "evaluation": r.evaluation,
                "objective_validation": r.objective_validation,
                "confidence": r.confidence,
                "model_version": r.model_version,
                "benchmark_version": r.benchmark_version,
                "prompt_version": r.prompt_version,
                "temperature": r.temperature,
                "top_p": r.top_p,
                "seed": r.seed,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost": r.estimated_cost,
                "retry_count": r.retry_count,
                "timeout_status": r.timeout_status,
            }
            metadata_json[key] = entry
        conn.execute(
            "INSERT INTO run_details (run_id, details, metadata) VALUES (?, ?, ?)",
            (run_id, json.dumps(details, default=_json_default), json.dumps(metadata_json, default=_json_default)),
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
    if conn is None:
        conn = _connect(db_path)
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
        r.metadata.setdefault("timestamp", run["timestamp"])
    if conn is not None:
        rows_details = conn.execute(
            "SELECT metadata FROM run_details WHERE run_id = ?", (run_id,)
        ).fetchone()
        if rows_details and rows_details["metadata"]:
            try:
                saved = json.loads(rows_details["metadata"])
                for key, entry in saved.items():
                    provider, model = key.split(":", 1)
                    target = next((x for x in results.values() if x.provider.value == provider and x.model == model), None)
                    if target is not None:
                        if entry.get("metadata"):
                            target.metadata.update(entry["metadata"])
                        target.evaluation = entry.get("evaluation", target.evaluation)
                        target.objective_validation = entry.get("objective_validation", target.objective_validation)
                        target.confidence = entry.get("confidence", target.confidence)
                        target.model_version = entry.get("model_version", target.model_version)
                        target.benchmark_version = entry.get("benchmark_version", target.benchmark_version)
                        target.prompt_version = entry.get("prompt_version", target.prompt_version)
                        target.temperature = entry.get("temperature", target.temperature)
                        target.top_p = entry.get("top_p", target.top_p)
                        target.seed = entry.get("seed", target.seed)
                        target.prompt_tokens = entry.get("prompt_tokens", target.prompt_tokens)
                        target.completion_tokens = entry.get("completion_tokens", target.completion_tokens)
                        target.total_tokens = entry.get("total_tokens", target.total_tokens)
                        target.estimated_cost = entry.get("estimated_cost", target.estimated_cost)
                        target.retry_count = entry.get("retry_count", target.retry_count)
                        target.timeout_status = entry.get("timeout_status", target.timeout_status)
            except Exception:
                pass
    return list(results.values())


def _json_default(value: Any) -> Any:
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, (datetime,)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
