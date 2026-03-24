# guardrails/input.py

import re
from dataclasses import dataclass
from logger import get_logger

log = get_logger("input_guardrail")

@dataclass
class InputValidationResult:
    is_valid: bool
    claim: str              # cleaned/normalized claim
    rejection_reason: str   # empty if valid
    risk_level: str         # "safe" | "low" | "medium" | "high"

class InputGuardrail:
    """
    Validates and sanitizes claims before the agent processes them.
    
    Three jobs:
    1. Reject prompt injections
    2. Reject non-claims (too short, nonsense, pure noise)
    3. Normalize valid claims for consistent processing
    """

    # Prompt injection patterns — attempts to hijack agent behavior

    INJECTION_PATTERNS = [
        r"ignore.{0,30}instructions",      # catches "ignore all previous instructions"
        r"ignore.{0,30}prompt",
        r"you are now",
        r"act as (a |an )?",
        r"forget (everything|all|your)",
        r"new (system |)prompt",
        r"disregard.{0,30}(instructions|prompt|rules)",
        r"override.{0,30}(instructions|prompt|rules)",
        r"jailbreak",
        r"do anything now",
        r"dan mode",
        r"pretend (you are|to be)",
        r"say (that |).{0,20}(is safe|is good|is true|is false)",  # catches "say vaccines are safe"
    ]

    # Claims that are requests, not claims
    REQUEST_PATTERNS = [
        r"^(tell|show|give|explain|describe|help|write|create|make) (me |us )?",
        r"^(what|how|why|when|where|who) (is|are|was|were|do|does|did|can|could|should|would)",
        r"^(can|could|would|should) you",
        r"^please ",
    ]

    MAX_LENGTH = 500    # characters
    MIN_LENGTH = 10     # characters

    def validate(self, raw_claim: str) -> InputValidationResult:
        """
        Full validation pipeline. Returns result with is_valid flag.
        Call this before passing anything to the agent.
        """
        log.info(f"Validating input: '{raw_claim[:80]}'")

        # ── Step 1: Basic sanity ───────────────────────────────────
        if not raw_claim or not raw_claim.strip():
            return self._reject("Empty claim", "safe")

        claim = raw_claim.strip()

        if len(claim) < self.MIN_LENGTH:
            return self._reject(
                f"Claim too short ({len(claim)} chars, min {self.MIN_LENGTH})",
                "safe"
            )

        if len(claim) > self.MAX_LENGTH:
            # Truncate rather than reject — might still be valid
            claim = claim[:self.MAX_LENGTH]
            log.warning(f"Claim truncated to {self.MAX_LENGTH} chars")

        # ── Step 2: Prompt injection detection ────────────────────
        claim_lower = claim.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, claim_lower):
                log.warning(f"Prompt injection detected: pattern '{pattern}'")
                return self._reject(
                    "Input contains instruction-like patterns. "
                    "Please submit a factual claim to audit.",
                    "high"
                )

        # ── Step 3: Request vs claim detection ────────────────────
        for pattern in self.REQUEST_PATTERNS:
            if re.search(pattern, claim_lower):
                return self._reject(
                    "This looks like a question or request. "
                    "Please submit a declarative claim to audit. "
                    "Example: '5G causes COVID-19' not 'Does 5G cause COVID-19?'",
                    "low"
                )

        # ── Step 4: Normalize ──────────────────────────────────────
        # Remove excessive whitespace
        claim = re.sub(r'\s+', ' ', claim).strip()
        # Remove surrounding quotes if present
        claim = claim.strip('"\'')

        log.info(f"Input validated successfully: '{claim[:80]}'")
        return InputValidationResult(
            is_valid=True,
            claim=claim,
            rejection_reason="",
            risk_level="safe",
        )

    def _reject(self, reason: str, risk_level: str) -> InputValidationResult:
        log.warning(f"Input rejected ({risk_level}): {reason}")
        return InputValidationResult(
            is_valid=False,
            claim="",
            rejection_reason=reason,
            risk_level=risk_level,
        )