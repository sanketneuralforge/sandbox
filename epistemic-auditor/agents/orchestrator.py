# agents/orchestrator.py — full updated file

import asyncio
from agents.decomposer import DecomposerAgent
from agents.archaeologist import ArchaeologistAgent
from agents.psychologist_writer import PsychologistWriterAgent
from memory.store import ClaimMemory
from guardrails.input import InputGuardrail
from guardrails.output import OutputGuardrail
from hitl.gate import HITLGate
from models import AuditResult, Verdict
from logger import get_logger
from config import HITL_ENABLED, HITL_CONFIDENCE_THRESHOLD
from memory.vector_store import AuditVectorStore

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
            import time
            start_time = time.time()

            # ── Input guardrail ────────────────────────────────────────
            validation = self.input_guard.validate(claim)
            if not validation.is_valid:
                log.warning(f"Input rejected: {validation.rejection_reason}")
                return self._rejected_result(claim, validation.rejection_reason)

            claim = validation.claim

            # ── Check exact/semantic cache ─────────────────────────────
            cached = self.memory.get(claim)
            if cached:
                log.info("Cache hit — returning stored result")
                print("[Orchestrator] Cache hit — returning stored result.")
                return AuditResult(**cached)

            # ── RAG: retrieve relevant past audits ─────────────────────
            # This runs BEFORE the agents so they have context
            print("[Orchestrator] Retrieving relevant past audits...")
            retrieved = self.vector_store.retrieve(claim)
            rag_context = self.vector_store.format_as_context(retrieved)

            if retrieved:
                print(f"[Orchestrator] Found {len(retrieved)} relevant past audits "
                    f"(top similarity: {retrieved[0]['similarity']:.3f})")
            else:
                print("[Orchestrator] No relevant past audits found — cold start")

            log.info(f"Starting full audit: '{claim}'")
            print(f"\n[Orchestrator] Starting full audit: '{claim}'")

            # ── Parallel execution with RAG context ───────────────────
            print("[Orchestrator] Running Decomposer + Archaeologist in parallel...")
            decomposition, archaeology = await asyncio.gather(
                self.decomposer.decompose(claim, rag_context=rag_context),
                self.archaeologist.trace(claim, rag_context=rag_context),
            )

            parallel_time = time.time() - start_time
            log.info(f"Parallel agents completed in {parallel_time:.1f}s")
            print(f"[Orchestrator] Parallel agents done in {parallel_time:.1f}s")

            # ── PsychologistWriter ─────────────────────────────────────
            print("[Orchestrator] Running PsychologistWriter...")
            psychology = await self.psych_writer.analyze(
                claim, decomposition, archaeology, rag_context=rag_context
            )

            # ── Assemble result ────────────────────────────────────────
            print("\n[Orchestrator] Assembling final report...")
            sources = [
                {
                    "title": p.source,
                    "url": p.url,
                    "credibility_score": p.credibility_score,
                }
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

            # ── Output guardrail ───────────────────────────────────────
            output_validation = self.output_guard.validate(result)

            if not output_validation.is_valid:
                log.error(f"Output blocked: {output_validation.blocking_issues}")
                return self._blocked_result(claim, output_validation.blocking_issues)

            if output_validation.warnings:
                for w in output_validation.warnings:
                    log.warning(f"Output warning: {w}")

            # ── HITL gate ──────────────────────────────────────────────
            if self.enable_hitl and self.hitl.should_interrupt(result, output_validation):
                decision = self.hitl.request_review(result, output_validation)
                if decision.action == "reject":
                    return self._rejected_result(
                        claim, f"Rejected by reviewer: {decision.notes}"
                    )

            # ── Store in both memory layers ────────────────────────────
            # JSON cache: exact/semantic lookup
            self.memory.store(claim, result.model_dump())
            # ChromaDB: RAG retrieval for future claims
            self.vector_store.store(result)

            # ── Gmail notification ─────────────────────────────────────
            await self._notify(result)

            total_time = time.time() - start_time
            log.info(f"Audit complete in {total_time:.1f}s. "
                    f"Verdict: {result.verdict} "
                    f"(confidence: {result.confidence:.2f})")
            print(f"\n[Orchestrator] Audit complete in {total_time:.1f}s. "
                f"Verdict: {result.verdict}")

            # Print vector store stats
            stats = self.vector_store.stats()
            print(f"[VectorStore] Total audits stored: {stats['total_audits']}")

            return result

    async def _notify(self, result: AuditResult):
        """
        Send audit report via Gmail MCP.
        Only fires for high-confidence FALSE verdicts — 
        these are the ones worth alerting on.
        """
        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                  else result.verdict

        if verdict == "FALSE" and result.confidence >= 0.7:
            try:
                from integrations.gmail_mcp import GmailMCP
                gmail = GmailMCP()
                await gmail.send_audit_report(result)
            except Exception as e:
                # Never let notification failure break the audit
                log.warning(f"Gmail notification failed (non-fatal): {e}")

    def _rejected_result(self, claim: str, reason: str) -> AuditResult:
        return AuditResult(
            claim_as_stated=claim,
            atomic_claims=[],
            verdict=Verdict.UNVERIFIABLE,
            confidence=0.0,
            evidence_summary=f"Audit could not proceed: {reason}",
            sources=[],
            why_people_believe_it="",
            counter_narrative="",
            origin_hypothesis="",
            timeline_summary="",
        )

    def _blocked_result(self, claim: str, issues: list) -> AuditResult:
        return AuditResult(
            claim_as_stated=claim,
            atomic_claims=[],
            verdict=Verdict.UNVERIFIABLE,
            confidence=0.0,
            evidence_summary=f"Output blocked by guardrail: {'; '.join(issues)}",
            sources=[],
            why_people_believe_it="",
            counter_narrative="",
            origin_hypothesis="",
            timeline_summary="",
        )