# observability/tracer.py

import json
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from logger import get_logger

log = get_logger("tracer")

@dataclass
class Span:
    """One unit of work within a trace."""
    trace_id: str
    span_id: str
    name: str
    agent: str
    start_time: float
    end_time: Optional[float] = None
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    status: str = "running"   # "running" | "success" | "error"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def finish(self, outputs: dict = None, error: str = None):
        self.end_time = time.time()
        self.status = "error" if error else "success"
        if outputs:
            self.outputs = outputs
        if error:
            self.error = error

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "agent": self.agent,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }

@dataclass
class Trace:
    """Complete record of one audit run."""
    trace_id: str
    claim: str
    start_time: float
    spans: list = field(default_factory=list)
    end_time: Optional[float] = None
    final_verdict: Optional[str] = None
    final_confidence: Optional[float] = None
    status: str = "running"
    rag_hits: int = 0
    cache_hit: bool = False

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def finish(self, verdict: str = None, confidence: float = None,
               status: str = "success"):
        self.end_time = time.time()
        self.status = status
        self.final_verdict = verdict
        self.final_confidence = confidence

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "claim": self.claim,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "final_verdict": self.final_verdict,
            "final_confidence": self.final_confidence,
            "status": self.status,
            "rag_hits": self.rag_hits,
            "cache_hit": self.cache_hit,
        }

class Tracer:
    """
    Manages traces for all agent runs.
    
    Usage:
        trace = tracer.start_trace(claim)
        span = tracer.start_span(trace, "decompose", "Decomposer")
        # ... do work ...
        tracer.finish_span(span, outputs={"verdict": "FALSE"})
        tracer.finish_trace(trace, verdict="FALSE", confidence=0.9)
    """

    TRACE_DIR = Path("observability/traces")

    def __init__(self):
        self.TRACE_DIR.mkdir(parents=True, exist_ok=True)
        self._active_traces: dict[str, Trace] = {}

    def start_trace(self, claim: str) -> Trace:
        trace_id = str(uuid.uuid4())[:8]  # short ID for readability
        trace = Trace(
            trace_id=trace_id,
            claim=claim,
            start_time=time.time(),
        )
        self._active_traces[trace_id] = trace
        log.info(f"Trace started: {trace_id} for '{claim[:50]}'")
        print(f"[Tracer] Trace {trace_id} started")
        return trace

    def start_span(self, trace: Trace, name: str, agent: str,
                   inputs: dict = None) -> Span:
        span = Span(
            trace_id=trace.trace_id,
            span_id=str(uuid.uuid4())[:8],
            name=name,
            agent=agent,
            start_time=time.time(),
            inputs=inputs or {},
        )
        trace.spans.append(span)
        return span

    def finish_span(self, span: Span, outputs: dict = None, error: str = None):
        span.finish(outputs=outputs, error=error)
        status = "✓" if span.status == "success" else "✗"
        log.info(f"Span {status} [{span.agent}] {span.name}: "
                 f"{span.duration_ms:.0f}ms")

    def finish_trace(self, trace: Trace, verdict: str = None,
                     confidence: float = None, status: str = "success"):
        trace.finish(verdict=verdict, confidence=confidence, status=status)
        self._save_trace(trace)
        self._active_traces.pop(trace.trace_id, None)
        log.info(f"Trace {trace.trace_id} finished: {status} "
                 f"in {trace.duration_ms:.0f}ms")
        print(f"[Tracer] Trace {trace.trace_id} saved "
              f"({trace.duration_ms:.0f}ms, {len(trace.spans)} spans)")

    def _save_trace(self, trace: Trace):
        path = self.TRACE_DIR / f"{trace.trace_id}.json"
        with open(path, "w") as f:
            json.dump(trace.to_dict(), f, indent=2)

    def load_traces(self, limit: int = 50) -> list[dict]:
        """Load recent traces for dashboard."""
        traces = []
        files = sorted(self.TRACE_DIR.glob("*.json"), 
                      key=lambda f: f.stat().st_mtime,
                      reverse=True)[:limit]
        for f in files:
            try:
                with open(f) as fp:
                    traces.append(json.load(fp))
            except Exception:
                pass
        return traces

# Global tracer instance — shared across all agents
tracer = Tracer()