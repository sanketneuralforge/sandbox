# evals/judge.py

from llm.client import LLMClient, Message
from models import AuditResult
from evals.dataset import EvalCase
import json
import re

JUDGE_PROMPT = """
You are an expert evaluator assessing the quality of a misinformation audit.
You will be given a claim, the expected verdict, and the agent's output.
Score each dimension from 0.0 to 1.0 and explain your reasoning briefly.

Respond ONLY with valid JSON matching this schema:
{
  "reasoning_quality": 0.0,
  "reasoning_notes": "one sentence",
  "counter_narrative_quality": 0.0,
  "counter_narrative_notes": "one sentence",
  "psychology_quality": 0.0,
  "psychology_notes": "one sentence",
  "overall_score": 0.0,
  "overall_notes": "one sentence"
}

Scoring guide:
- reasoning_quality: Is the evidence_summary accurate and well-reasoned?
- counter_narrative_quality: Does it use the same emotional register as the claim? Is it compelling?
- psychology_quality: Is the why_people_believe_it analysis insightful and empathetic?
- overall_score: Your holistic assessment of the full audit quality
"""

class LLMJudge:

    def __init__(self):
        self.llm = LLMClient()

    async def judge(self, case: EvalCase, result: AuditResult) -> dict:
        """
        Ask the LLM to score the quality of the audit result.
        This is Level 3 eval — end-to-end quality assessment.
        """
        user_message = f"""
Claim: "{case.claim}"
Expected verdict: {case.expected_verdict}
Category: {case.category}

Agent output:
- Verdict: {result.verdict}
- Confidence: {result.confidence}
- Evidence summary: {result.evidence_summary}
- Why people believe it: {result.why_people_believe_it}
- Counter-narrative: {result.counter_narrative}
- Atomic claims found: {result.atomic_claims}

Score this audit on the dimensions specified.
"""
        messages = [Message(role="user", content=user_message)]

        try:
            response = await self.llm.complete(
                messages=messages,
                system_prompt=JUDGE_PROMPT,
                max_tokens=512,
            )
            # Extract JSON
            cleaned = re.sub(r"```(?:json)?", "", response).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            return json.loads(cleaned[start:end])

        except Exception as e:
            print(f"  [Judge] Scoring failed: {e}")
            return {
                "reasoning_quality": 0.0,
                "counter_narrative_quality": 0.0,
                "psychology_quality": 0.0,
                "overall_score": 0.0,
                "overall_notes": f"Judge failed: {e}",
            }