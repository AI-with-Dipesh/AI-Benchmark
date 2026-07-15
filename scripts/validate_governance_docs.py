"""CI validation script for governance document persistence policy."""

from __future__ import annotations

import sys
from pathlib import Path

REVIEWS_DIR = Path("docs/reviews")
ROOT_GOVERNANCE_PATTERNS = ("sprint-*.md", "release-*.md", "SPRINT*.md", "RELEASE*.md")


def check_governance_docs() -> list[str]:
    issues: list[str] = []
    if not REVIEWS_DIR.is_dir():
        issues.append("Missing governance directory: docs/reviews/")
        return issues

    required = ["sprint-9-technical-debt.md"]
    for name in required:
        if not (REVIEWS_DIR / name).exists():
            issues.append(f"Missing required governance document: docs/reviews/{name}")

    for pattern in ROOT_GOVERNANCE_PATTERNS:
        for path in Path(".").glob(pattern):
            if path.parent == Path(".") and path.is_file():
                issues.append(
                    f"Governance document outside reviews directory: {path}"
                )
    return issues


def main() -> int:
    issues = check_governance_docs()
    if issues:
        print("Governance persistence validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Governance persistence validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
