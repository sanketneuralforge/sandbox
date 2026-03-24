# main.py

import asyncio
import json
from agent.core import EpistemicAuditor

async def main():
    auditor = EpistemicAuditor()

    claims = [
        "5G towers were used to spread COVID-19",
        "5G towers were used to spread COVID-19",  # second time — should hit cache
        "Drinking bleach cures cancer",
    ]

    for claim in claims:
        print("\n" + "=" * 60)
        result = await auditor.audit(claim)
        print("\n── AUDIT RESULT ──")
        print(json.dumps(result.model_dump(), indent=2))
        print(f"\nMemory stats: {auditor.memory.stats()}")

if __name__ == "__main__":
    asyncio.run(main())