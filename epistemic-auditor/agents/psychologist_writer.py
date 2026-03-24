from agents.base import BaseAgent
from agents.prompts import PSYCHOLOGIST_WRITER_PROMPT
from models import PsychologyResult, DecompositionResult, ArchaeologyResult


class PsychologistWriterAgent(BaseAgent):
    name = "PsychologistWriter"
    # No tools - this agent reasons, not researches

    def get_system_prompt(self) -> str:
        return PSYCHOLOGIST_WRITER_PROMPT

    async def analyze(
        self,
        claim: str,
        decomposition: DecompositionResult,
        archaeology: ArchaeologyResult,
    ) -> PsychologyResult:
        print("\n[PsychologistWriter] Analyzing belief patterns...")

        # This agent gets the findings from other agents as context
        # This is the key pattern: agents pass state to each other
        context = f"""
Claim: "{claim}"

Verdict from Decomposer: {decomposition.overall_verdict}
Atomic claims found: {[c.text for c in decomposition.atomic_claims]}

Origin hypothesis: {archaeology.origin_hypothesis}
How it spread: {archaeology.timeline_summary}

Now explain why people believe this and write a counter-narrative.
"""
        response = await self.run(context)
        data = self._extract_json(response)

        return PsychologyResult(
            why_people_believe_it=data.get("why_people_believe_it", ""),
            emotional_hook=data.get("emotional_hook", ""),
            counter_narrative=data.get("counter_narrative", ""),
        )
# agents/psychologist_writer.py

from agents.base import BaseAgent
from agents.prompts import PSYCHOLOGIST_WRITER_PROMPT
from models import PsychologyResult, DecompositionResult, ArchaeologyResult

class PsychologistWriterAgent(BaseAgent):
    name = "PsychologistWriter"
    # No tools — this agent reasons, not researches

    def get_system_prompt(self) -> str:
        return PSYCHOLOGIST_WRITER_PROMPT

    async def analyze(
        self,
        claim: str,
        decomposition,
        archaeology,
        rag_context: str = "",
    ) -> PsychologyResult:
        print(f"\n[PsychologistWriter] Analyzing belief patterns...")

        context = f"""
    Claim: "{claim}"
    Verdict from Decomposer: {decomposition.overall_verdict}
    Atomic claims found: {[c.text for c in decomposition.atomic_claims]}
    Origin hypothesis: {archaeology.origin_hypothesis}
    How it spread: {archaeology.timeline_summary}

    Now explain why people believe this and write a counter-narrative.
    """
        response = await self.run(context, rag_context=rag_context)
        data = self._extract_json(response)

        return PsychologyResult(
            why_people_believe_it=data.get("why_people_believe_it", ""),
            emotional_hook=data.get("emotional_hook", ""),
            counter_narrative=data.get("counter_narrative", ""),
        )