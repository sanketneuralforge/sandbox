# main.py

import asyncio
import json
import time
from agents.orchestrator import OrchestratorAgent

async def main():
    orchestrator = OrchestratorAgent(enable_hitl=False)

    # Run two related claims back to back.
    # Second claim should retrieve first as RAG context.
    claims = [
        "Vaccines cause autism",                          # cold start
        "The MMR vaccine causes developmental disorders", # should retrieve first
        "The flu shot causes neurological damage",        # should retrieve both
    ]

    for claim in claims:
        print("\n" + "=" * 60)
        start = time.time()
        result = await orchestrator.audit(claim)
        elapsed = time.time() - start

        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                  else result.verdict

        print(f"\n── RESULT ({elapsed:.1f}s) ──")
        print(json.dumps({
            "verdict": verdict,
            "confidence": result.confidence,
            "counter_narrative": result.counter_narrative,
        }, indent=2))

if __name__ == "__main__":
    asyncio.run(main())