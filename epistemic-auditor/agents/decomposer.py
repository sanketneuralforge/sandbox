# agents/decomposer.py

from agents.base import BaseAgent
from agents.prompts import DECOMPOSER_PROMPT
from tools.registry import ToolRegistry
from models import DecompositionResult, AtomicClaim, Verdict

class DecomposerAgent(BaseAgent):
    name = "Decomposer"

    def __init__(self):
        super().__init__()
        self.tools = ToolRegistry()

    def get_system_prompt(self) -> str:
        return DECOMPOSER_PROMPT.format(
            tool_descriptions=self.tools.tool_descriptions
        )

    async def decompose(self, claim: str, rag_context: str = "") -> DecompositionResult:
        print(f"\n[Decomposer] Starting on: '{claim[:60]}...'")
        response = await self.run(
            f'Decompose and verify this claim: "{claim}"',
            rag_context=rag_context,
        )
        data = self._extract_json(response)

        # Parse into typed model with safe fallbacks
        atomic_claims = [
            AtomicClaim(
                text=c.get("text", ""),
                verdict=Verdict(c.get("verdict", "UNVERIFIABLE")),
                evidence=c.get("evidence", "")
            )
            for c in data.get("atomic_claims", [])
        ]

        return DecompositionResult(
            original_claim=data.get("original_claim", claim),
            atomic_claims=atomic_claims,
            overall_verdict=Verdict(data.get("overall_verdict", "UNVERIFIABLE")),
            confidence=float(data.get("confidence", 0.0)),
        )