# agents/orchestrator.py

from agents.decomposer import DecomposerAgent
from agents.archaeologist import ArchaeologistAgent
from agents.psychologist_writer import PsychologistWriterAgent
from memory.store import ClaimMemory
from models import AuditResult, Verdict

class OrchestratorAgent:
    """
    Coordinates the three specialist agents.
    
    Current execution: sequential (clear to debug)
    Stage 7 upgrade: parallel (2x faster)
    
    Key responsibility: passing the right state to each agent.
    The PsychologistWriter needs the Decomposer's verdict.
    The final assembly needs everything.
    """

    def __init__(self):
        self.decomposer   = DecomposerAgent()
        self.archaeologist = ArchaeologistAgent()
        self.psych_writer  = PsychologistWriterAgent()
        self.memory        = ClaimMemory()

    async def audit(self, claim: str) -> AuditResult:

        # ── Check memory ───────────────────────────────────────────
        cached = self.memory.get(claim)
        if cached:
            print("[Orchestrator] Cache hit — returning stored result.")
            return AuditResult(**cached)

        print(f"\n[Orchestrator] Starting full audit: '{claim}'")
        print("[Orchestrator] Step 1/3: Decomposing claim...")

        # ── Step 1: Decompose + verify ─────────────────────────────
        decomposition = await self.decomposer.decompose(claim)

        print("[Orchestrator] Step 2/3: Tracing origin...")

        # ── Step 2: Trace propagation ──────────────────────────────
        archaeology = await self.archaeologist.trace(claim)

        print("[Orchestrator] Step 3/3: Analyzing psychology + writing counter-narrative...")

        # ── Step 3: Psychology + counter-narrative ─────────────────
        # Notice: this agent receives OTHER agents' outputs as input
        # This is message passing — the core of multi-agent coordination
        psychology = await self.psych_writer.analyze(
            claim, decomposition, archaeology
        )

        # ── Assemble final result ──────────────────────────────────
        print("\n[Orchestrator] Assembling final report...")

        # Collect all sources from propagation points
        sources = [
            {
                "title": p.source,
                "url": p.url,
                "credibility_score": p.credibility_score
            }
            for p in archaeology.propagation_points
        ]

        # Build evidence summary from atomic claims
        evidence_parts = [
            f"{c.text}: {c.verdict.value}"
            for c in decomposition.atomic_claims[:3]
        ]
        evidence_summary = " | ".join(evidence_parts)

        result = AuditResult(
            claim_as_stated=claim,
            atomic_claims=[c.text for c in decomposition.atomic_claims],
            verdict=decomposition.overall_verdict,
            confidence=decomposition.confidence,
            evidence_summary=evidence_summary,
            sources=sources,
            why_people_believe_it=psychology.why_people_believe_it,
            counter_narrative=psychology.counter_narrative,
            origin_hypothesis=archaeology.origin_hypothesis,
            timeline_summary=archaeology.timeline_summary,
        )

        # ── Store in memory ────────────────────────────────────────
        self.memory.store(claim, result.model_dump())

        print(f"\n[Orchestrator] Audit complete. Verdict: {result.verdict}")
        return result