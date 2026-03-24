# models.py

from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Verdict(str, Enum):
    TRUE          = "TRUE"
    FALSE         = "FALSE"
    MISLEADING    = "MISLEADING"
    UNVERIFIABLE  = "UNVERIFIABLE"

class AtomicClaim(BaseModel):
    """A single falsifiable sub-claim extracted from the original."""
    text: str
    verdict: Optional[Verdict] = None
    evidence: Optional[str] = None

class PropagationPoint(BaseModel):
    """One node in the claim's spread timeline."""
    source: str
    url: str
    credibility_score: float
    role: str   # "origin" | "amplifier" | "debunker"

class DecompositionResult(BaseModel):
    """Output of the Decomposer agent."""
    original_claim: str
    atomic_claims: list[AtomicClaim]
    overall_verdict: Verdict
    confidence: float

class ArchaeologyResult(BaseModel):
    """Output of the Archaeologist agent."""
    origin_hypothesis: str
    propagation_points: list[PropagationPoint]
    timeline_summary: str

class PsychologyResult(BaseModel):
    """Output of the Psychologist+Writer agent."""
    why_people_believe_it: str
    emotional_hook: str        # the core emotional appeal of the claim
    counter_narrative: str     # uses same emotional register

class AuditResult(BaseModel):
    claim_as_stated: str
    atomic_claims: list[str]
    verdict: Verdict
    confidence: float
    evidence_summary: str
    sources: list[dict]
    why_people_believe_it: str
    counter_narrative: str
    origin_hypothesis: str = "Not analyzed"   # ← default
    timeline_summary: str = ""                # ← default