# guardrails/output.py

import re
from dataclasses import dataclass, field
from models import AuditResult, Verdict
from logger import get_logger

log = get_logger("output_guardrail")

@dataclass
class OutputValidationResult:
    is_valid: bool
    warnings: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    requires_human_review: bool = False
    review_reason: str = ""

class OutputGuardrail:
    """
    Validates audit results before they reach the user.
    
    Two tiers:
    - Warnings: noted but don't block output
    - Blocking issues: output is held for human review
    """

    # Confidence below this triggers human review
    LOW_CONFIDENCE_THRESHOLD = 0.4

    # Confidence above this for TRUE/FALSE requires strong evidence
    HIGH_CONFIDENCE_THRESHOLD = 0.9

    def validate(self, result: AuditResult) -> OutputValidationResult:
        log.info(f"Validating output for: '{result.claim_as_stated[:60]}'")

        warnings = []
        blocking = []
        requires_review = False
        review_reason = ""

        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                  else result.verdict

        # ── Check 1: Empty critical fields ────────────────────────
        if not result.atomic_claims:
            blocking.append("No atomic claims produced — agent may have failed to decompose")

        if not result.evidence_summary or len(result.evidence_summary) < 20:
            blocking.append("Evidence summary missing or too thin")

        if not result.counter_narrative or \
           result.counter_narrative == "This claim could not be analyzed at this time.":
            warnings.append("Counter-narrative is placeholder — quality may be low")

        # ── Check 2: Confidence calibration ───────────────────────
        if result.confidence < self.LOW_CONFIDENCE_THRESHOLD and \
           verdict in ("TRUE", "FALSE"):
            requires_review = True
            review_reason = (
                f"Low confidence ({result.confidence:.2f}) for definitive "
                f"verdict '{verdict}' — human review recommended"
            )

        if result.confidence == 0.0 and verdict != "UNVERIFIABLE":
            blocking.append(
                f"Zero confidence with non-UNVERIFIABLE verdict '{verdict}' "
                f"— likely a parsing failure"
            )

        # ── Check 3: Source quality ────────────────────────────────
        if verdict in ("TRUE", "FALSE") and not result.sources:
            requires_review = True
            review_reason = (
                f"Definitive verdict '{verdict}' with no cited sources"
            )

        # Check for suspiciously generic URLs
        suspicious_patterns = [
            r"example\.com",
            r"placeholder",
            r"source\d+",
            r"url\.com",
        ]
        for source in result.sources:
            url = source.get("url", "")
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    blocking.append(f"Suspicious placeholder URL detected: {url}")

        # ── Check 4: High confidence sanity check ─────────────────
        if result.confidence >= self.HIGH_CONFIDENCE_THRESHOLD and \
           len(result.sources) < 2:
            warnings.append(
                f"High confidence ({result.confidence:.2f}) but fewer than "
                f"2 sources — consider adding more evidence"
            )

        # ── Check 5: Verdict-confidence alignment ─────────────────
        if verdict == "UNVERIFIABLE" and result.confidence > 0.7:
            warnings.append(
                "UNVERIFIABLE verdict with high confidence is contradictory"
            )

        is_valid = len(blocking) == 0

        if not is_valid:
            log.warning(f"Output blocked: {blocking}")
        elif requires_review:
            log.info(f"Output flagged for review: {review_reason}")
        else:
            log.info("Output validated successfully")

        return OutputValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            blocking_issues=blocking,
            requires_human_review=requires_review,
            review_reason=review_reason,
        )