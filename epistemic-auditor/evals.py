# run_evals.py

import asyncio
import os
from pathlib import Path
from evals.harness import EvalHarness
from evals.dataset import EVAL_DATASET

async def main():
    # One case per category
    seen_categories = set()
    subset = []
    for case in EVAL_DATASET:
        if case.category not in seen_categories:
            subset.append(case)
            seen_categories.add(case.category)

    print(f"Running {len(subset)} cases (one per category):")
    for c in subset:
        print(f"  [{c.category}] {c.claim[:50]}...")

    harness = EvalHarness(use_llm_judge=True)
    report = await harness.run(cases=subset)

    print(f"\nFinal score: {report['level1_average']:.0%} L1 | "
          f"{report['level3_average']:.0%} L3")

if __name__ == "__main__":
    # Clear checkpoint from previous run
    checkpoint = Path("evals/reports/checkpoint.json")
    if checkpoint.exists():
        try:
            checkpoint.unlink()
            print("Previous checkpoint cleared.")
        except Exception:
            pass

    asyncio.run(main())