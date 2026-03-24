# hitl/gate.py

from dataclasses import dataclass
from models import AuditResult
from guardrails.output import OutputValidationResult
from logger import get_logger

log = get_logger("hitl_gate")

@dataclass
class HITLDecision:
    action: str           # "approve" | "reject" | "revise"
    reviewer: str         # who made the decision
    notes: str            # reviewer's comments
    modified_result: AuditResult = None  # if action is "revise"

class HITLGate:
    """
    Human-in-the-loop interrupt gate.
    
    In production this would:
    - Send an email/Slack notification to a reviewer
    - Wait for async approval via a webhook
    - Timeout after N minutes and escalate
    
    For development, we use CLI prompts.
    The interface is identical — swap the I/O mechanism for production.
    """

    def should_interrupt(self, result, validation) -> bool:
        if validation.requires_human_review:
            return True

        if result.confidence < 0.5:   # was 0.3 — raise threshold
            return True

        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                else result.verdict

        # Ambiguous category always gets review
        if verdict == "MISLEADING":
            return True

        if verdict == "UNVERIFIABLE" and result.confidence < 0.7:
            return True

        return False

    def request_review(
        self,
        result: AuditResult,
        validation: OutputValidationResult,
    ) -> HITLDecision:
        """
        Presents the audit to a human and collects their decision.
        CLI implementation — replace with async webhook for production.
        """
        log.info(f"HITL interrupt triggered for: '{result.claim_as_stated[:60]}'")

        print("\n" + "="*60)
        print("⚠️  HUMAN REVIEW REQUIRED")
        print("="*60)
        print(f"\nClaim: {result.claim_as_stated}")
        print(f"Verdict: {result.verdict} (confidence: {result.confidence:.2f})")
        print(f"Review reason: {validation.review_reason}")

        if validation.warnings:
            print(f"\nWarnings:")
            for w in validation.warnings:
                print(f"  ⚠ {w}")

        print(f"\nEvidence summary: {result.evidence_summary}")
        print(f"Counter-narrative: {result.counter_narrative}")

        print("\nOptions:")
        print("  [a] Approve — send to user as-is")
        print("  [r] Reject  — discard this audit")
        print("  [s] Skip    — approve with a warning note")

        while True:
            choice = input("\nYour decision [a/r/s]: ").strip().lower()

            if choice == "a":
                notes = input("Approval notes (optional): ").strip()
                log.info(f"HITL approved by human. Notes: {notes}")
                return HITLDecision(
                    action="approve",
                    reviewer="human",
                    notes=notes or "Approved by reviewer",
                )

            elif choice == "r":
                notes = input("Rejection reason: ").strip()
                log.info(f"HITL rejected by human. Reason: {notes}")
                return HITLDecision(
                    action="reject",
                    reviewer="human",
                    notes=notes,
                )

            elif choice == "s":
                log.info("HITL skipped — approved with warning")
                return HITLDecision(
                    action="approve",
                    reviewer="human",
                    notes="Auto-approved with low confidence warning",
                )

            else:
                print("Please enter 'a', 'r', or 's'")