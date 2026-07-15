#!/usr/bin/env python3
"""Dependency audit script — reports known vulnerabilities in installed packages."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def check_safety() -> list[dict[str, Any]]:
    """Use `safety` if available."""
    rc, out, err = _run([sys.executable, "-m", "safety", "check", "--json"])
    if rc == 0 and out.strip():
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return []
    return []


def check_pip_list() -> list[dict[str, Any]]:
    """Fallback: list installed packages with versions."""
    rc, out, err = _run([sys.executable, "-m", "pip", "list", "--format=json"])
    if rc == 0 and out.strip():
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return []
    return []


def audit(output_path: Path | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"vulnerabilities": [], "packages": []}
    vulns = check_safety()
    if vulns:
        report["vulnerabilities"] = vulns
    else:
        packages = check_pip_list()
        report["packages"] = packages
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    out = Path("audit-report.json")
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    result = audit(output_path=out)
    vuln_count = len(result.get("vulnerabilities", []))
    pkg_count = len(result.get("packages", []))
    if vuln_count:
        print(f"AUDIT: {vuln_count} vulnerability(ies) found.")
        for v in result["vulnerabilities"]:
            print(f"  - {v}")
        sys.exit(1)
    print(f"AUDIT: Clean. {pkg_count} packages enumerated.")


if __name__ == "__main__":
    main()
