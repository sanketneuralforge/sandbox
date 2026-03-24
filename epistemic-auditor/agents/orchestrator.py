# agents/orchestrator.py

from agents.decomposer import DecomposerAgent
from agents.archaeologist import ArchaeologistAgent
from agents.psychologist_writer import PsychologistWriterAgent
from memory.store import ClaimMemory
from guardrails.input import InputGuardrail
from guardrails.output import OutputGuardrail
from hitl.gate import HITLGate
from models import AuditResult, Verdict
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
        self.enable_hitl   = enable_hitl

    async def audit(self, claim: str) -> AuditResult:

        # ── Input guardrail ────────────────────────────────────────
        validation = self.input_guard.validate(claim)
        if not validation.is_valid:
            log.warning(f"Input rejected: {validation.rejection_reason}")
            return self._rejected_result(claim, validation.rejection_reason)

        # Use the normalized claim from here on
        claim = validation.claim

        # ── Check memory ───────────────────────────────────────────
        cached = self.memory.get(claim)
        if cached:
            log.info("Cache hit — returning stored result")
            print("[Orchestrator] Cache hit — returning stored result.")
            return AuditResult(**cached)

        log.info(f"Starting full audit: '{claim}'")
        print(f"\n[Orchestrator] Starting full audit: '{claim}'")

        # ── Run the three agents ───────────────────────────────────
        print("[Orchestrator] Step 1/3: Decomposing claim...")
        decomposition = await self.decomposer.decompose(claim)

        print("[Orchestrator] Step 2/3: Tracing origin...")
        archaeology = await self.archaeologist.trace(claim)

        print("[Orchestrator] Step 3/3: Analyzing psychology...")
        psychology = await self.psych_writer.analyze(
            claim, decomposition, archaeology
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
            print(f"\n[Guardrail] Output blocked: {output_validation.blocking_issues}")
            return self._blocked_result(claim, output_validation.blocking_issues)

        if output_validation.warnings:
            for w in output_validation.warnings:
                log.warning(f"Output warning: {w}")
                print(f"[Guardrail] Warning: {w}")

        # ── HITL gate ──────────────────────────────────────────────
        if self.enable_hitl and self.hitl.should_interrupt(result, output_validation):
            decision = self.hitl.request_review(result, output_validation)

            if decision.action == "reject":
                log.info("Audit rejected by human reviewer")
                return self._rejected_result(claim, f"Rejected by reviewer: {decision.notes}")

            log.info(f"Audit approved by human reviewer: {decision.notes}")

        # ── Store and return ───────────────────────────────────────
        self.memory.store(claim, result.model_dump())
        log.info(f"Audit complete. Verdict: {result.verdict} "
                 f"(confidence: {result.confidence:.2f})")
        print(f"\n[Orchestrator] Audit complete. Verdict: {result.verdict}")
        return result

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