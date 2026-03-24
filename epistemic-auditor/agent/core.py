# agent/core.py

import json
import re
from llm.client import LLMClient, Message
from tools.registry import ToolRegistry
from memory.store import ClaimMemory
from agent.prompts import EPISTEMIC_AUDITOR_SYSTEM_PROMPT
from pydantic import BaseModel

class AuditResult(BaseModel):
    claim_as_stated: str
    atomic_claims: list[str]
    verdict: str
    confidence: float
    evidence_summary: str
    sources: list[dict]
    why_people_believe_it: str
    counter_narrative: str

class EpistemicAuditor:
    
    MAX_TOOL_TURNS = 6   # safety limit — agent can't loop forever

    def __init__(self):
        self.llm = LLMClient()
        self.tools = ToolRegistry()
        self.memory = ClaimMemory()

    async def audit(self, claim: str) -> AuditResult:
        
        # ── Check memory first ─────────────────────────────────────
        cached = self.memory.get(claim)
        if cached:
            print("[Agent] Returning cached result.")
            return AuditResult(**cached)

        print(f"\n[Agent] Auditing: '{claim}'")

        # ── Build the system prompt with tool descriptions ─────────
        system_prompt = EPISTEMIC_AUDITOR_SYSTEM_PROMPT.format(
            tool_descriptions=self.tools.tool_descriptions
        )

        # ── Start the conversation ─────────────────────────────────
        messages = [
            Message(role="user", content=f'Audit this claim: "{claim}"')
        ]

        # ── The agent loop ─────────────────────────────────────────
        for turn in range(self.MAX_TOOL_TURNS):
            print(f"[Agent] Turn {turn + 1}/{self.MAX_TOOL_TURNS}")

            response = await self.llm.complete(
                messages=messages,
                system_prompt=system_prompt,
            )

            # Add the agent's response to conversation history
            # This is context management — the agent sees its own reasoning
            messages.append(Message(role="assistant", content=response))

            # ── Did the agent call a tool? ─────────────────────────
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_name, argument = tool_call
                print(f"[Agent] Calling tool: {tool_name}({argument[:50]}...)")

                result = self.tools.execute(tool_name, argument)

                # Feed tool result back as a user message
                # This is how the agent "observes" what happened
                messages.append(Message(
                    role="user",
                    content=f"Tool result for {tool_name}:\n{result}"
                ))
                continue

            # ── Did the agent give a final answer? ─────────────────
            if "FINAL_ANSWER:" in response:
                audit = self._parse_final_answer(response, claim)
                # Store in memory
                self.memory.store(claim, audit.model_dump())
                return audit

            # ── Agent responded with neither — nudge it ────────────
            # Production gotcha: without this nudge, some models just
            # chat back at you instead of using tools or answering.
            messages.append(Message(
                role="user",
                content="Please continue. Either call a tool or provide FINAL_ANSWER: with your JSON."
            ))

        # ── Safety: max turns reached ──────────────────────────────
        print("[Agent] Max turns reached. Returning partial result.")
        return self._fallback(claim)

    def _parse_tool_call(self, response: str) -> tuple[str, str] | None:
        """
        Detects if the LLM wants to call a tool.
        Expected format: TOOL_CALL: tool_name("argument")
        """
        match = re.search(
            r'TOOL_CALL:\s*(\w+)\s*\(([^)]+)\)',
            response,
            re.IGNORECASE
        )
        if match:
            return match.group(1), match.group(2)
        return None

    def _parse_final_answer(self, response: str, claim: str) -> AuditResult:
        """
        Extracts JSON from the FINAL_ANSWER section.
        Same robust parsing as Stage 2.
        """
        try:
            after_marker = response.split("FINAL_ANSWER:")[-1].strip()
            cleaned = re.sub(r"```(?:json)?", "", after_marker).strip()
            cleaned = cleaned.rstrip("`").strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            json_str = cleaned[start:end]
            return AuditResult(**json.loads(json_str))
        except Exception as e:
            print(f"[Agent] Final answer parse failed: {e}")
            return self._fallback(claim)

    def _fallback(self, claim: str) -> AuditResult:
        return AuditResult(
            claim_as_stated=claim,
            atomic_claims=[claim],
            verdict="UNVERIFIABLE",
            confidence=0.0,
            evidence_summary="Agent could not complete the audit.",
            sources=[],
            why_people_believe_it="Unknown.",
            counter_narrative="This claim could not be analyzed at this time.",
        )