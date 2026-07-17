from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import RegressionRecord
from aibenchmark.app.history import load_latest

logger = logging.getLogger(__name__)


class RegressionDetector:
    def __init__(self, manager: AutomationManager | None = None, threshold_pct: float = 10.0, history_db_path: Path | None = None) -> None:
        self.manager = manager or AutomationManager()
        self.threshold_pct = threshold_pct
        self.history_db_path = history_db_path

    def detect(self, execution_id: int, current_results: list[Any]) -> list[RegressionRecord]:
        kwargs: dict[str, Any] = {}
        if self.history_db_path is not None:
            kwargs["db_path"] = self.history_db_path
        latest = load_latest(2, **kwargs)
        if len(latest) < 2:
            return []
        previous = latest[1]
        previous_map = {r.model: r for r in previous}
        regressions: list[RegressionRecord] = []
        for result in current_results:
            prev = previous_map.get(result.model)
            if prev is None:
                continue
            if prev.overall > 0 and result.overall < prev.overall * (1 - self.threshold_pct / 100):
                delta = ((result.overall - prev.overall) / prev.overall) * 100
                regressions.append(
                    RegressionRecord(
                        execution_id=execution_id,
                        benchmark_name=result.model,
                        metric="overall",
                        previous_value=prev.overall,
                        current_value=result.overall,
                        delta_pct=delta,
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        severity="high" if abs(delta) > 25 else "medium",
                    )
                )
        for reg in regressions:
            self.manager.record_regression(reg)
        return regressions

