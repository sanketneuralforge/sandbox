# main.py

import asyncio
import json
from agent.core import EpistemicAuditor

async def main():
    auditor = EpistemicAuditor()

    # Test claims — try changing these
    test_claims = [
        "5G towers were used to spread COVID-19",
        "The Great Wall of China is visible from space",
    ]

    for claim in test_claims:
        print("\n" + "="*60)
        result = await auditor.audit(claim)

        # Pretty print the result
        print("\n── AUDIT RESULT ──")
        print(json.dumps(result.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())