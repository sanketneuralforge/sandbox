# evals/metrics.py

from models import AuditResult
from evals.dataset import EvalCase

def score_verdict(result: AuditResult, case: EvalCase) -> dict:
    """
    Level 1 eval: did we get the right verdict?
    
    We don't penalize MISLEADING vs TRUE/FALSE harshly because
    a reasonable agent might classify ambiguous claims differently.
    We use a soft scoring system.
    """
    expected = case.expected_verdict
    actual = result.verdict.value if hasattr(result.verdict, 'value') else result.verdict

    if actual == expected:
        score = 1.0
        notes = "Exact match"
    elif _is_adjacent(actual, expected):
        # e.g. MISLEADING vs FALSE — related but not identical
        score = 0.5
        notes = f"Adjacent verdict (got {actual}, expected {expected})"
    else:
        score = 0.0
        notes = f"Wrong verdict (got {actual}, expected {expected})"

    return {"score": score, "notes": notes, "expected": expected, "actual": actual}

def score_atomic_claims(result: AuditResult, case: EvalCase) -> dict:
    """
    Level 1 eval: did the agent decompose the claim properly?
    """
    actual_count = len(result.atomic_claims)
    expected_min = case.expected_min_atomic

    if actual_count >= expected_min:
        score = 1.0
        notes = f"Found {actual_count} atomic claims (min: {expected_min})"
    elif actual_count > 0:
        score = 0.5
        notes = f"Found {actual_count} atomic claims (below min: {expected_min})"
    else:
        score = 0.0
        notes = f"No atomic claims found (min: {expected_min})"

    return {"score": score, "notes": notes}

def score_sources(result: AuditResult, case: EvalCase) -> dict:
    """
    Level 1 eval: did the agent cite sources when it should have?
    """
    has_sources = len(result.sources) > 0

    if not case.should_have_sources:
        return {"score": 1.0, "notes": "Sources not required for this case"}

    if has_sources:
        # Check that at least one source has a real URL
        real_urls = [
            s for s in result.sources
            if s.get("url", "").startswith("http")
        ]
        if real_urls:
            score = 1.0
            notes = f"Found {len(real_urls)} sources with valid URLs"
        else:
            score = 0.5
            notes = "Sources present but no valid URLs"
    else:
        score = 0.0
        notes = "No sources found — required for this case"

    return {"score": score, "notes": notes}

def score_confidence(result: AuditResult, case: EvalCase) -> dict:
    """
    Level 1 eval: is the confidence calibrated?
    
    We don't expect a specific number — we check that:
    - UNVERIFIABLE claims have low confidence (< 0.5)
    - Clear TRUE/FALSE claims have high confidence (> 0.6)
    """
    verdict = result.verdict.value if hasattr(result.verdict, 'value') else result.verdict
    conf = result.confidence

    if verdict == "UNVERIFIABLE":
        score = 1.0 if conf < 0.5 else 0.0
        notes = f"Confidence {conf:.2f} {'appropriate' if conf < 0.5 else 'too high'} for UNVERIFIABLE"
    elif verdict in ("TRUE", "FALSE"):
        score = 1.0 if conf >= 0.6 else 0.5
        notes = f"Confidence {conf:.2f} for {verdict}"
    else:
        score = 1.0  # MISLEADING — any confidence is acceptable
        notes = f"Confidence {conf:.2f} for MISLEADING"

    return {"score": score, "notes": notes}

def score_counter_narrative(result: AuditResult, case: EvalCase) -> dict:
    """
    Level 1 eval: basic quality check on counter-narrative.
    Not semantic — just structure checks.
    Full semantic scoring is done by LLM-as-judge.
    """
    cn = result.counter_narrative

    if not cn or cn == "This claim could not be analyzed at this time.":
        return {"score": 0.0, "notes": "No counter-narrative produced"}

    if len(cn) < 20:
        return {"score": 0.5, "notes": f"Counter-narrative too short ({len(cn)} chars)"}

    if len(cn) > 500:
        return {"score": 0.5, "notes": "Counter-narrative too long (>500 chars)"}

    return {"score": 1.0, "notes": f"Counter-narrative present ({len(cn)} chars)"}

def _is_adjacent(actual: str, expected: str) -> bool:
    """MISLEADING is adjacent to both TRUE and FALSE."""
    adjacencies = {
        ("MISLEADING", "FALSE"), ("FALSE", "MISLEADING"),
        ("MISLEADING", "TRUE"),  ("TRUE", "MISLEADING"),
    }
    return (actual, expected) in adjacencies