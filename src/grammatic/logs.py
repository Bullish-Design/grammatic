from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BuildQueryEvent(BaseModel):
    """Build log schema used by query and reporting commands."""

    model_config = ConfigDict(extra="ignore")

    event_type: Literal["build"] = "build"
    grammar: str = Field(min_length=1)
    status: Literal["success", "failure"]
    duration_ms: int = Field(ge=0)
    timestamp: str


class ParseQueryEvent(BaseModel):
    """Parse log schema used by query and reporting commands."""

    model_config = ConfigDict(extra="ignore")

    event_type: Literal["parse"] = "parse"
    grammar: str = Field(min_length=1)
    status: Literal["success", "failure"] = "success"
    duration_ms: int = Field(ge=0)
    has_errors: bool = False
    grammar_version: str | None = None
    timestamp: str


class SummaryMetrics(BaseModel):
    """Aggregate metrics over a set of workflow events."""

    total: int
    success_count: int
    failure_count: int
    success_rate: float
    latency_ms: dict[str, float]


class LogRepository:
    """Repository for typed JSONL log reads and query metrics."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.logs_dir = (repo_root / "logs").resolve()
        self.builds_path = self.logs_dir / "builds.jsonl"
        self.parses_path = self.logs_dir / "parses.jsonl"

    @staticmethod
    def _load_jsonl(path: Path, model: type[BuildQueryEvent] | type[ParseQueryEvent]) -> list[BuildQueryEvent] | list[ParseQueryEvent]:
        if not path.exists():
            return []

        entries: list[BuildQueryEvent] | list[ParseQueryEvent] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                entries.append(model.model_validate(payload))
            except Exception as exc:
                raise ValueError(f"Invalid log entry at {path}:{line_no}: {exc}") from exc
        return entries

    @staticmethod
    def _apply_limit(items: list, limit: int | None) -> list:
        if limit is None:
            return items
        return items[-limit:]

    def recent_builds(self, *, limit: int | None = 10, grammar: str | None = None) -> list[BuildQueryEvent]:
        items = self._load_jsonl(self.builds_path, BuildQueryEvent)
        filtered = [entry for entry in items if not grammar or entry.grammar == grammar]
        return self._apply_limit(filtered, limit)

    def recent_parses(
        self,
        *,
        limit: int | None = 10,
        grammar: str | None = None,
        failures_only: bool = False,
    ) -> list[ParseQueryEvent]:
        items = self._load_jsonl(self.parses_path, ParseQueryEvent)
        filtered = [entry for entry in items if not grammar or entry.grammar == grammar]
        if failures_only:
            filtered = [entry for entry in filtered if entry.status == "failure" or entry.has_errors]
        return self._apply_limit(filtered, limit)

    def build_metrics(self, *, grammar: str | None = None) -> tuple[SummaryMetrics, dict[str, int]]:
        items = self._load_jsonl(self.builds_path, BuildQueryEvent)
        filtered = [entry for entry in items if not grammar or entry.grammar == grammar]
        status_counts = Counter(entry.status for entry in filtered)
        return self._metrics(filtered), dict(status_counts)

    def parse_metrics(self, *, grammar: str | None = None) -> tuple[SummaryMetrics, dict[str, int]]:
        items = self._load_jsonl(self.parses_path, ParseQueryEvent)
        filtered = [entry for entry in items if not grammar or entry.grammar == grammar]

        failure_count = sum(1 for entry in filtered if entry.status == "failure" or entry.has_errors)
        success_count = max(len(filtered) - failure_count, 0)
        success_rate = (success_count / len(filtered) * 100.0) if filtered else 0.0
        durations = sorted(entry.duration_ms for entry in filtered)

        metrics = SummaryMetrics(
            total=len(filtered),
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_rate, 2),
            latency_ms={
                "p50": self._percentile(durations, 50),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99),
            },
        )
        status_counts = Counter(
            "failure" if entry.status == "failure" or entry.has_errors else "success" for entry in filtered
        )
        return metrics, dict(status_counts)

    def build_success_rate_counts(self, *, grammar: str) -> list[dict[str, int | bool]]:
        """Compatibility helper for legacy `just build-success-rate` output shape."""

        _, counts = self.build_metrics(grammar=grammar)
        output: list[dict[str, int | bool]] = []
        if "success" in counts:
            output.append({"success": True, "count": counts["success"]})
        if "failure" in counts:
            output.append({"success": False, "count": counts["failure"]})
        return output

    def parse_average_duration_ms(self, *, grammar: str) -> float:
        """Compatibility helper for legacy `just avg-parse-time` output shape."""

        items = self._load_jsonl(self.parses_path, ParseQueryEvent)
        filtered = [entry.duration_ms for entry in items if entry.grammar == grammar]
        if not filtered:
            return 0.0
        return round(sum(filtered) / len(filtered), 2)

    def _metrics(self, items: list[BuildQueryEvent]) -> SummaryMetrics:
        success_count = sum(1 for entry in items if entry.status == "success")
        failure_count = sum(1 for entry in items if entry.status == "failure")
        success_rate = (success_count / len(items) * 100.0) if items else 0.0
        durations = sorted(entry.duration_ms for entry in items)

        return SummaryMetrics(
            total=len(items),
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_rate, 2),
            latency_ms={
                "p50": self._percentile(durations, 50),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99),
            },
        )

    @staticmethod
    def _percentile(values: list[int], percentile: int) -> float:
        if not values:
            return 0.0
        if len(values) == 1:
            return float(values[0])
        rank = (percentile / 100.0) * (len(values) - 1)
        lower_index = math.floor(rank)
        upper_index = math.ceil(rank)
        if lower_index == upper_index:
            return float(values[lower_index])
        weight = rank - lower_index
        interpolated = values[lower_index] * (1.0 - weight) + values[upper_index] * weight
        return round(float(interpolated), 2)
