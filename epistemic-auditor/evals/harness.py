# evals/harness.py

import json
import asyncio
from datetime import datetime
from pathlib import Path

from agents.orchestrator import OrchestratorAgent
from evals.dataset import EVAL_DATASET, EvalCase
from evals.metrics import (
    score_verdict, score_atomic_claims,
    score_sources, score_confidence, score_counter_narrative
)
from evals.judge import LLMJudge
from models import AuditResult

class EvalHarness:

    def __init__(self, use_llm_judge: bool = True):
        self.orchestrator = OrchestratorAgent()
        self.judge = LLMJudge() if use_llm_judge else None
        self.results = []

    async def run(self, cases=None):
        cases = cases or EVAL_DATASET
        
        # ── Resume from checkpoint if it exists ───────────────────
        checkpoint_path = Path("evals/reports/checkpoint.json")
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path) as f:
                    content = f.read().strip()
                    self.results = json.loads(content) if content else []
            except (json.JSONDecodeError, Exception):
                print("Checkpoint corrupted — starting fresh.")
                self.results = []
                checkpoint_path.unlink()
            
            completed_ids = {r["case_id"] for r in self.results}
            cases = [c for c in cases if c.id not in completed_ids]
            print(f"Resuming from checkpoint — {len(self.results)} done, "
          f"{len(cases)} remaining")

        for case in cases:
            result = await self._run_single(case)
            self.results.append(result)

        report = self._compile_report()
        self._print_report(report)
        self._save_report(report)
        
        # Clean up checkpoint after successful completion
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        
        return report

    async def _run_single(self, case: EvalCase) -> dict:
        print(f"\n── {case.id}: {case.claim[:50]}...")
        print(f"   Category: {case.category} | Expected: {case.expected_verdict}")

        # Run the agent
        try:
            audit = await self.orchestrator.audit(case.claim)
        except Exception as e:
            print(f"   [ERROR] Agent failed: {e}")
            audit = None

        if audit is None:
            return self._failed_case(case)

        # ── Level 1: deterministic metrics ────────────────────────
        verdict_score    = score_verdict(audit, case)
        atomic_score     = score_atomic_claims(audit, case)
        sources_score    = score_sources(audit, case)
        confidence_score = score_confidence(audit, case)
        cn_score         = score_counter_narrative(audit, case)

        level1_avg = (
            verdict_score["score"] +
            atomic_score["score"] +
            sources_score["score"] +
            confidence_score["score"] +
            cn_score["score"]
        ) / 5

        print(f"   Verdict:    {verdict_score['actual']} "
              f"({'✓' if verdict_score['score'] == 1.0 else '~' if verdict_score['score'] == 0.5 else '✗'})"
              f" — {verdict_score['notes']}")
        print(f"   Atomics:    {atomic_score['notes']}")
        print(f"   Sources:    {sources_score['notes']}")
        print(f"   Confidence: {confidence_score['notes']}")
        print(f"   Counter-N:  {cn_score['notes']}")
        print(f"   L1 score:   {level1_avg:.2f}")

        # ── Level 3: LLM-as-judge ──────────────────────────────────
        judge_scores = {}
        if self.judge:
            print(f"   Running LLM judge...")
            judge_scores = await self.judge.judge(case, audit)
            print(f"   L3 score:   {judge_scores.get('overall_score', 0):.2f}"
                  f" — {judge_scores.get('overall_notes', '')}")

        result = {
            "case_id": case.id,
            "claim": case.claim,
            "category": case.category,
            "expected_verdict": case.expected_verdict,
            "actual_verdict": verdict_score["actual"],
            "level1": {
                "verdict": verdict_score,
                "atomic_claims": atomic_score,
                "sources": sources_score,
                "confidence": confidence_score,
                "counter_narrative": cn_score,
                "average": level1_avg,
            },
            "level3": judge_scores,
            "audit_output": audit.model_dump(),
        }
        
        # ── Checkpoint immediately after each case ─────────────────
        self._checkpoint(result)

        return result

    def _checkpoint(self, result: dict):
        """Save result immediately so crashes don't lose progress."""
        path = Path("evals/reports/checkpoint.json")
        existing = []
        if path.exists():
            with open(path) as f:
                existing = json.load(f)
        existing.append(result)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    def _compile_report(self) -> dict:
        """Aggregate scores across all cases."""
        total = len(self.results)
        if total == 0:
            return {}

        # Level 1 averages
        l1_scores = [r["level1"]["average"] for r in self.results]
        l1_avg = sum(l1_scores) / total

        # Verdict accuracy
        verdict_hits = sum(
            1 for r in self.results
            if r["level1"]["verdict"]["score"] == 1.0
        )

        # Level 3 averages
        l3_scores = [
            r["level3"].get("overall_score", 0)
            for r in self.results
            if r.get("level3")
        ]
        l3_avg = sum(l3_scores) / len(l3_scores) if l3_scores else 0

        # By category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r["level1"]["average"])

        cat_scores = {
            cat: sum(scores) / len(scores)
            for cat, scores in categories.items()
        }

        return {
            "run_at": datetime.now().isoformat(),
            "total_cases": total,
            "verdict_accuracy": verdict_hits / total,
            "level1_average": l1_avg,
            "level3_average": l3_avg,
            "by_category": cat_scores,
            "cases": self.results,
        }

    def _print_report(self, report: dict):
        print(f"\n{'='*60}")
        print("EVAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total cases:       {report['total_cases']}")
        print(f"Verdict accuracy:  {report['verdict_accuracy']:.0%}")
        print(f"Level 1 avg:       {report['level1_average']:.2f}/1.00")
        print(f"Level 3 avg:       {report['level3_average']:.2f}/1.00")
        print(f"\nBy category:")
        for cat, score in report["by_category"].items():
            bar = "█" * int(score * 20)
            print(f"  {cat:<15} {bar:<20} {score:.2f}")

    def _save_report(self, report: dict):
        path = Path("evals/reports")
        path.mkdir(parents=True, exist_ok=True)
        filename = path / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {filename}")

    def _failed_case(self, case: EvalCase) -> dict:
        return {
            "case_id": case.id,
            "claim": case.claim,
            "category": case.category,
            "expected_verdict": case.expected_verdict,
            "actual_verdict": "ERROR",
            "level1": {"average": 0.0},
            "level3": {},
        }