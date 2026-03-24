# agents/archaeologist.py

from agents.base import BaseAgent
from agents.prompts import ARCHAEOLOGIST_PROMPT
from tools.registry import ToolRegistry
from models import ArchaeologyResult, PropagationPoint

class ArchaeologistAgent(BaseAgent):
    name = "Archaeologist"

    def __init__(self):
        super().__init__()
        self.tools = ToolRegistry()

    def get_system_prompt(self) -> str:
        return ARCHAEOLOGIST_PROMPT.format(
            tool_descriptions=self.tools.tool_descriptions
        )

    async def trace(self, claim: str) -> ArchaeologyResult:
        print(f"\n[Archaeologist] Tracing origin of: '{claim[:60]}...'")
        response = await self.run(f'Trace the origin and spread of: "{claim}"')
        data = self._extract_json(response)

        points = [
            PropagationPoint(
                source=p.get("source", ""),
                url=p.get("url", ""),
                credibility_score=float(p.get("credibility_score", 0.5)),
                role=p.get("role", "amplifier"),
            )
            for p in data.get("propagation_points", [])
        ]

        return ArchaeologyResult(
            origin_hypothesis=data.get("origin_hypothesis", "Unknown"),
            propagation_points=points,
            timeline_summary=data.get("timeline_summary", ""),
        )