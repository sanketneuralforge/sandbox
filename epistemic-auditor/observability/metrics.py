# observability/metrics.py

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from logger import get_logger

log = get_logger("metrics")

@dataclass
class RunMetrics:
    """Metrics for a single audit run."""
    trace_id: str
    claim: str
    verdict: str
    confidence: float
    total_duration_ms: float
    decomposer_duration_ms: float = 0.0
    archaeologist_duration_ms: float = 0.0
    psych_writer_duration_ms: float = 0.0
    tool_calls: int = 0
    tool_errors: int = 0
    llm_turns: int = 0
    rag_hits: int = 0
    cache_hit: bool = False
    guardrail_blocked: bool = False
    hitl_triggered: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

class MetricsStore:
    """
    Persists and aggregates run metrics.
    
    In production this would write to:
    - Prometheus (for alerting)
    - DataDog (for dashboards)
    - CloudWatch (for AWS)
    
    For development, we write to a JSON file and
    compute aggregates on read.
    """

    METRICS_FILE = Path("observability/metrics.json")

    def __init__(self):
        self.METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._runs: list[dict] = self._load()

    def _load(self) -> list:
        if self.METRICS_FILE.exists():
            try:
                with open(self.METRICS_FILE) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.METRICS_FILE, "w") as f:
            json.dump(self._runs, f, indent=2)

    def record(self, metrics: RunMetrics):
        """Record metrics for one run."""
        self._runs.append(metrics.__dict__)
        self._save()
        log.info(
            f"Metrics recorded: verdict={metrics.verdict} "
            f"duration={metrics.total_duration_ms:.0f}ms "
            f"tools={metrics.tool_calls} rag={metrics.rag_hits}"
        )

    def compute_aggregates(self, last_n: int = 100) -> dict:
        """
        Compute aggregate metrics over last N runs.
        These are your production health indicators.
        """
        runs = self._runs[-last_n:]
        if not runs:
            return {}

        total = len(runs)
        completed = [r for r in runs if not r.get("guardrail_blocked")]
        cache_hits = [r for r in runs if r.get("cache_hit")]
        rag_hits_runs = [r for r in runs if r.get("rag_hits", 0) > 0]
        errors = [r for r in runs if r.get("verdict") == "UNVERIFIABLE"]
        hitl_runs = [r for r in runs if r.get("hitl_triggered")]

        durations = [r["total_duration_ms"] for r in completed if r.get("total_duration_ms")]
        durations_sorted = sorted(durations)

        tool_errors = sum(r.get("tool_errors", 0) for r in runs)
        tool_calls = sum(r.get("tool_calls", 0) for r in runs)

        verdict_counts = {}
        for r in runs:
            v = r.get("verdict", "UNKNOWN")
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        return {
            "total_runs": total,
            "completion_rate": len(completed) / total if total else 0,
            "cache_hit_rate": len(cache_hits) / total if total else 0,
            "rag_hit_rate": len(rag_hits_runs) / total if total else 0,
            "error_rate": len(errors) / total if total else 0,
            "hitl_rate": len(hitl_runs) / total if total else 0,
            "tool_error_rate": tool_errors / tool_calls if tool_calls else 0,
            "latency_p50_ms": durations_sorted[int(len(durations_sorted) * 0.5)] if durations_sorted else 0,
            "latency_p95_ms": durations_sorted[int(len(durations_sorted) * 0.95)] if durations_sorted else 0,
            "verdict_distribution": verdict_counts,
            "avg_tool_calls": tool_calls / total if total else 0,
            "avg_rag_hits": sum(r.get("rag_hits", 0) for r in runs) / total if total else 0,
        }

# Global metrics store
metrics_store = MetricsStore()