# agents/orchestrator.py — full updated file

import asyncio
import time
from agents.decomposer import DecomposerAgent
from agents.archaeologist import ArchaeologistAgent
from agents.psychologist_writer import PsychologistWriterAgent
from memory.store import ClaimMemory
from memory.vector_store import AuditVectorStore
from guardrails.input import InputGuardrail
from guardrails.output import OutputGuardrail
from hitl.gate import HITLGate
from observability.tracer import tracer
from observability.metrics import metrics_store, RunMetrics
from models import AuditResult, Verdict
from config import HITL_ENABLED
from logger import get_logger


log = get_logger("orchestrator")

class OrchestratorAgent:

    def __init__(self, enable_hitl: bool = True):
        self.decomposer    = DecomposerAgent()
        self.archaeologist = ArchaeologistAgent()
        self.psych_writer  = PsychologistWriterAgent()
        self.memory        = ClaimMemory()
        self.input_guard   = InputGuardrail()
        self.output_guard  = OutputGuardrail()
        self.hitl          = HITLGate()
        self.enable_hitl = enable_hitl if enable_hitl is not None else HITL_ENABLED
        self.vector_store = AuditVectorStore()

    async def audit(self, claim: str) -> AuditResult:
            start_time = time.time()
            # ── Start trace ────────────────────────────────────────────
            trace = tracer.start_trace(claim)

            # Track metrics as we go
            tool_calls = 0
            tool_errors = 0
            llm_turns = 0
            hitl_triggered = False
            guardrail_blocked = False

            try:
                # ── Input guardrail ────────────────────────────────────
                span = tracer.start_span(trace, "input_validation", "InputGuardrail",
                                        inputs={"claim": claim})
                validation = self.input_guard.validate(claim)
                tracer.finish_span(span, outputs={
                    "is_valid": validation.is_valid,
                    "risk_level": validation.risk_level,
                })

                if not validation.is_valid:
                    guardrail_blocked = True
                    tracer.finish_trace(trace, status="blocked")
                    self._record_metrics(
                        trace, claim, "UNVERIFIABLE", 0.0,
                        start_time, guardrail_blocked=True
                    )
                    return self._rejected_result(claim, validation.rejection_reason)

                claim = validation.claim

                # ── Cache check ────────────────────────────────────────
                span = tracer.start_span(trace, "cache_lookup", "Memory",
                                        inputs={"claim": claim})
                cached = self.memory.get(claim)
                tracer.finish_span(span, outputs={"cache_hit": cached is not None})

                if cached:
                    trace.cache_hit = True
                    tracer.finish_trace(
                        trace,
                        verdict=cached.get("verdict"),
                        confidence=cached.get("confidence"),
                    )
                    self._record_metrics(
                        trace, claim,
                        cached.get("verdict", "UNKNOWN"),
                        cached.get("confidence", 0.0),
                        start_time, cache_hit=True
                    )
                    return AuditResult(**cached)

                # ── RAG retrieval ──────────────────────────────────────
                span = tracer.start_span(trace, "rag_retrieval", "VectorStore",
                                        inputs={"claim": claim})
                retrieved = self.vector_store.retrieve(claim)
                rag_context = self.vector_store.format_as_context(retrieved)
                trace.rag_hits = len(retrieved)
                tracer.finish_span(span, outputs={
                    "hits": len(retrieved),
                    "top_similarity": retrieved[0]["similarity"] if retrieved else 0,
                })

                if retrieved:
                    print(f"[Orchestrator] Found {len(retrieved)} relevant past audits")
                else:
                    print("[Orchestrator] No relevant past audits — cold start")

                print(f"\n[Orchestrator] Starting full audit: '{claim}'")

                # ── Parallel: Decomposer + Archaeologist ───────────────
                decomp_span = tracer.start_span(
                    trace, "decompose", "Decomposer",
                    inputs={"claim": claim, "rag_hits": len(retrieved)}
                )
                arch_span = tracer.start_span(
                    trace, "trace_origin", "Archaeologist",
                    inputs={"claim": claim, "rag_hits": len(retrieved)}
                )

                print("[Orchestrator] Running Decomposer + Archaeologist in parallel...")
                decomposition, archaeology = await asyncio.gather(
                    self.decomposer.decompose(claim, rag_context=rag_context),
                    self.archaeologist.trace(claim, rag_context=rag_context),
                )

                tracer.finish_span(decomp_span, outputs={
                    "atomic_claims": len(decomposition.atomic_claims),
                    "verdict": decomposition.overall_verdict.value,
                })
                tracer.finish_span(arch_span, outputs={
                    "propagation_points": len(archaeology.propagation_points),
                    "origin": archaeology.origin_hypothesis[:100],
                })

                parallel_time = time.time() - start_time
                print(f"[Orchestrator] Parallel agents done in {parallel_time:.1f}s")

                # ── PsychologistWriter ─────────────────────────────────
                psych_span = tracer.start_span(
                    trace, "analyze_psychology", "PsychologistWriter",
                    inputs={"verdict": decomposition.overall_verdict.value}
                )
                print("[Orchestrator] Running PsychologistWriter...")
                psychology = await self.psych_writer.analyze(
                    claim, decomposition, archaeology, rag_context=rag_context
                )
                tracer.finish_span(psych_span, outputs={
                    "counter_narrative": psychology.counter_narrative[:100],
                })

                # ── Assemble result ────────────────────────────────────
                sources = [
                    {"title": p.source, "url": p.url,
                    "credibility_score": p.credibility_score}
                    for p in archaeology.propagation_points
                ]
                evidence_parts = [
                    f"{c.text}: {c.verdict.value}"
                    for c in decomposition.atomic_claims[:3]
                ]

                result = AuditResult(
                    claim_as_stated=claim,
                    atomic_claims=[c.text for c in decomposition.atomic_claims],
                    verdict=decomposition.overall_verdict,
                    confidence=decomposition.confidence,
                    evidence_summary=" | ".join(evidence_parts),
                    sources=sources,
                    why_people_believe_it=psychology.why_people_believe_it,
                    counter_narrative=psychology.counter_narrative,
                    origin_hypothesis=archaeology.origin_hypothesis,
                    timeline_summary=archaeology.timeline_summary,
                )

                # ── Output guardrail ───────────────────────────────────
                span = tracer.start_span(trace, "output_validation", "OutputGuardrail",
                                        inputs={"verdict": result.verdict.value
                                        if hasattr(result.verdict, 'value')
                                        else result.verdict})
                output_validation = self.output_guard.validate(result)
                tracer.finish_span(span, outputs={
                    "is_valid": output_validation.is_valid,
                    "warnings": len(output_validation.warnings),
                    "requires_review": output_validation.requires_human_review,
                })

                if not output_validation.is_valid:
                    guardrail_blocked = True
                    tracer.finish_trace(trace, status="blocked")
                    self._record_metrics(
                        trace, claim, "UNVERIFIABLE", 0.0,
                        start_time, guardrail_blocked=True
                    )
                    return self._blocked_result(claim, output_validation.blocking_issues)

                # ── HITL ───────────────────────────────────────────────
                if self.enable_hitl and self.hitl.should_interrupt(
                    result, output_validation
                ):
                    hitl_triggered = True
                    span = tracer.start_span(trace, "hitl_review", "HITLGate")
                    decision = self.hitl.request_review(result, output_validation)
                    tracer.finish_span(span, outputs={"decision": decision.action})

                    if decision.action == "reject":
                        tracer.finish_trace(trace, status="rejected")
                        return self._rejected_result(
                            claim, f"Rejected: {decision.notes}"
                        )

                # ── Store in both layers ───────────────────────────────
                self.memory.store(claim, result.model_dump())
                self.vector_store.store(result)

                # ── Notify ─────────────────────────────────────────────
                await self._notify(result)

                # ── Finish trace ───────────────────────────────────────
                verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                        else result.verdict
                tracer.finish_trace(
                    trace,
                    verdict=verdict,
                    confidence=result.confidence,
                    status="success",
                )

                # ── Record metrics ─────────────────────────────────────
                self._record_metrics(
                    trace, claim, verdict, result.confidence,
                    start_time,
                    rag_hits=len(retrieved),
                    hitl_triggered=hitl_triggered,
                )

                total_time = time.time() - start_time
                print(f"\n[Orchestrator] Audit complete in {total_time:.1f}s. "
                    f"Verdict: {result.verdict}")
                return result

            except Exception as e:
                log.error(f"Audit failed: {e}", exc_info=True)
                tracer.finish_trace(trace, status="error")
                raise

    def _record_metrics(
        self, trace, claim: str, verdict: str, confidence: float,
        start_time: float, cache_hit: bool = False,
        rag_hits: int = 0, guardrail_blocked: bool = False,
        hitl_triggered: bool = False,
    ):
        total_ms = (time.time() - start_time) * 1000

        # Extract per-agent durations from spans
        def span_ms(name):
            for s in trace.spans:
                if s.name == name and s.end_time:
                    return s.duration_ms
            return 0.0

        metrics_store.record(RunMetrics(
            trace_id=trace.trace_id,
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            total_duration_ms=total_ms,
            decomposer_duration_ms=span_ms("decompose"),
            archaeologist_duration_ms=span_ms("trace_origin"),
            psych_writer_duration_ms=span_ms("analyze_psychology"),
            rag_hits=rag_hits,
            cache_hit=cache_hit,
            guardrail_blocked=guardrail_blocked,
            hitl_triggered=hitl_triggered,
        ))


    async def _notify(self, result: AuditResult):
        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                  else result.verdict
        if verdict == "FALSE" and result.confidence >= 0.7:
            try:
                from integrations.gmail_mcp import GmailMCP
                await GmailMCP().send_audit_report(result)
            except Exception as e:
                log.warning(f"Gmail notification failed (non-fatal): {e}")

    def _rejected_result(self, claim: str, reason: str) -> AuditResult:
        return AuditResult(
            claim_as_stated=claim, atomic_claims=[],
            verdict=Verdict.UNVERIFIABLE, confidence=0.0,
            evidence_summary=f"Audit could not proceed: {reason}",
            sources=[], why_people_believe_it="",
            counter_narrative="", origin_hypothesis="",
            timeline_summary="",
        )

    def _blocked_result(self, claim: str, issues: list) -> AuditResult:
            return AuditResult(
                claim_as_stated=claim, atomic_claims=[],
                verdict=Verdict.UNVERIFIABLE, confidence=0.0,
                evidence_summary=f"Output blocked: {'; '.join(issues)}",
                sources=[], why_people_believe_it="",
                counter_narrative="", origin_hypothesis="",
                timeline_summary="",
            )