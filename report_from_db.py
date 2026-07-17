#!/usr/bin/env python3
"""Generate benchmark reports from history DB with corrected aggregate scores."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB = Path("/home/Doom/.local/share/aibenchmark/history.db")
OUT = Path("/home/Doom/AI-Benchmark/reports")
OUT.mkdir(exist_ok=True)


def load_model_runs() -> dict[str, dict]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load all runs
    cur.execute("SELECT run_id, timestamp, provider, model, overall, benchmark_count FROM runs ORDER BY run_id")
    runs = [dict(r) for r in cur.fetchall()]

    # Load all scores
    cur.execute("SELECT run_id, benchmark, raw, normalized, weight, weighted FROM benchmark_scores")
    scores_by_run = {}
    for row in cur.fetchall():
        scores_by_run.setdefault(row["run_id"], []).append(dict(row))

    conn.close()

    # Build model aggregates (latest run per provider:model)
    model_data: dict[str, dict] = {}
    for run in runs:
        key = f"{run['provider']}:{run['model']}"
        scores = scores_by_run.get(run["run_id"], [])
        total_weight = sum(s["weight"] for s in scores)
        weighted_sum = sum(s["weighted"] for s in scores)
        corrected_overall = weighted_sum / total_weight if total_weight else 0.0

        entry = {
            "run_id": run["run_id"],
            "timestamp": run["timestamp"],
            "provider": run["provider"],
            "model": run["model"],
            "stored_overall": run["overall"],
            "corrected_overall": round(corrected_overall, 4),
            "benchmark_count": run["benchmark_count"],
            "total_weight": total_weight,
            "weighted_sum": round(weighted_sum, 4),
            "scores": {},
        }
        for s in scores:
            entry["scores"][s["benchmark"]] = {
                "raw": round(s["raw"], 4),
                "normalized": round(s["normalized"], 4),
                "weight": s["weight"],
                "weighted": round(s["weighted"], 4),
            }
        model_data[key] = entry

    return model_data


def generate_execution_report(model_data: dict[str, dict]) -> str:
    valid = [v for v in model_data.values() if v["benchmark_count"] >= 9]
    valid.sort(key=lambda x: x["corrected_overall"], reverse=True)

    lines = [
        "# AI-Benchmark Execution Report (Sprint 11.5 Fixed)",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Platform**: AI-Benchmark v2.0.0",
        f"**Models with complete data**: {len(valid)}",
        "",
        "---",
        "",
        "## Model Rankings (Corrected Overall)",
        "",
        "| Rank | Model | Corrected Overall | Coding | Debugging | Reasoning | Research | Code Review | JSON | Instruction | General | Latency |",
        "|------|-------|-------------------|--------|-----------|-----------|----------|-------------|------|-------------|---------|---------|",
    ]
    for i, m in enumerate(valid, 1):
        s = m["scores"]
        def fmt(cat):
            if cat not in s:
                return "N/A"
            v = s[cat]
            if cat == "latency":
                return f"{v['normalized']:.3f}"
            return f"{v['raw']:.3f}"
        lines.append(
            f"| {i} | {m['model']} | {m['corrected_overall']:.4f} | {fmt('coding')} | {fmt('debugging')} | {fmt('reasoning')} | {fmt('research')} | {fmt('code_review')} | {fmt('json')} | {fmt('instruction')} | {fmt('general')} | {fmt('latency')} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Corrected Overall uses raw scores for non-latency categories; latency uses stored normalized score.",
        "- The `runs.overall` field previously stored 0.0 due to a normalization bug; now fixed in engine.py.",
        "- Weights: coding 25, debugging 20, reasoning 15, research 15, code_review 10, latency 10, json 5, instruction 5, general 5.",
        "- Only completed runs with 9 benchmark categories are included.",
    ]
    return "\n".join(lines)


def main():
    model_data = load_model_runs()
    report = generate_execution_report(model_data)
    out_path = OUT / "execution-report.md"
    out_path.write_text(report)
    print(f"Wrote {out_path}")
    print(f"Total runs in DB: {len(model_data)}")

    json_path = OUT / "execution-results.json"
    json_path.write_text(json.dumps(list(model_data.values()), indent=2))
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
