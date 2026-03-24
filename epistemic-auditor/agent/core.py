# agent/core.py

import json
import re
from llm.client import LLMClient, Message
from tools.search import WebSearchTool
from pydantic import BaseModel
from typing import Optional

# ── output schema (Pydantic validates the LLM's JSON output) ──────
class AuditResult(BaseModel):
    claim_as_stated: str
    atomic_claims: list[str]
    verdict: str
    confidence: float
    evidence_summary: str
    sources: list[dict]
    why_people_believe_it: str
    counter_narrative: str

# ── the agent ─────────────────────────────────────────────────────
class EpistemicAuditor:
    """
    The minimal agent loop:
    
    1. OBSERVE  — receive a claim
    2. ACT      — search for evidence  
    3. OBSERVE  — read search results
    4. THINK    — reason about evidence
    5. ACT      — produce structured audit
    """

    def __init__(self):
        self.llm = LLMClient()
        self.search = WebSearchTool()

    async def audit(self, claim: str) -> AuditResult:
        """
        Full audit pipeline for a single claim.
        This is the agent loop — one pass for now, multi-pass in Stage 3.
        """
        print(f"\n[Agent] Auditing claim: '{claim}'")

        # ── STEP 1: OBSERVE — we have the raw claim ───────────────
        # Nothing to do yet, we just received it.

        # ── STEP 2: ACT — search for evidence ────────────────────
        print("[Agent] Searching for evidence...")
        search_query = self._build_search_query(claim)
        results = self.search.run(search_query)
        print(f"[Agent] Found {len(results)} results")

        # ── STEP 3: OBSERVE — read the search results ─────────────
        evidence_text = self.search.format_for_prompt(results)

        # ── STEP 4 & 5: THINK + ACT — reason and produce output ───
        print("[Agent] Reasoning about evidence...")
        raw_response = await self._reason(claim, evidence_text)

        # ── Parse and validate the output ─────────────────────────
        audit = self._parse_output(raw_response, claim)
        print(f"[Agent] Done. Verdict: {audit.verdict} (confidence: {audit.confidence})")
        return audit

    def _build_search_query(self, claim: str) -> str:
        """
        Turns a raw claim into a good search query.
        
        Interview trap: agents that just search the claim verbatim
        get worse results than agents that reformulate the query.
        Example: "5G causes COVID" → "5G towers COVID-19 scientific evidence fact check"
        
        For MVP we do a simple reformulation. In Stage 3 we'll let the 
        LLM decide what to search for.
        """
        # Strip question marks, add fact-check framing
        clean = claim.rstrip("?").strip()
        return f"{clean} fact check evidence scientific"

    async def _reason(self, claim: str, evidence: str) -> str:
        """
        Core LLM call: give it the claim + evidence, get back JSON.
        
        This is where the prompt engineering lives.
        """
        from agent.prompts import EPISTEMIC_AUDITOR_SYSTEM_PROMPT

        user_message = f"""
Claim to audit: "{claim}"

Search results:
{evidence}

Produce your audit as JSON following the schema in your instructions.
"""
        messages = [Message(role="user", content=user_message)]

        response = await self.llm.complete(
            messages=messages,
            system_prompt=EPISTEMIC_AUDITOR_SYSTEM_PROMPT,
        )
        return response

    def _parse_output(self, raw: str, original_claim: str) -> AuditResult:
        """
        Parses and validates the LLM's JSON output.
        
        Production gotcha: LLMs often wrap JSON in ```json ``` blocks
        or add explanation text before/after. We strip all that.
        
        If parsing fails entirely, we return a safe fallback —
        NEVER let a parse error crash the agent.
        """
        # Try to extract JSON from the response
        # Pattern: find the first { and last } in the response
        try:
            # Remove markdown code blocks if present
            cleaned = re.sub(r"```(?:json)?", "", raw).strip()
            cleaned = cleaned.rstrip("`").strip()

            # Find JSON object boundaries
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = cleaned[start:end]
            data = json.loads(json_str)
            return AuditResult(**data)

        except Exception as e:
            print(f"[Agent] Parse failed: {e}")
            print(f"[Agent] Raw response was:\n{raw[:500]}")

            # Safe fallback — the agent failed gracefully
            return AuditResult(
                claim_as_stated=original_claim,
                atomic_claims=[original_claim],
                verdict="UNVERIFIABLE",
                confidence=0.0,
                evidence_summary="Agent failed to parse a structured response.",
                sources=[],
                why_people_believe_it="Unknown — parsing failed.",
                counter_narrative="This claim could not be analyzed at this time.",
            )