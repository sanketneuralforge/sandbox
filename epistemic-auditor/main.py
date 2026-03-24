# main.py

import asyncio
import json
from agents.orchestrator import OrchestratorAgent

async def main():
    orchestrator = OrchestratorAgent()

    claims = [
        "5G towers were used to spread COVID-19",
        "5G towers spread COVID-19",
        "Vaccines cause autism",
    ]

    for claim in claims:
        print("\n" + "=" * 60)
        result = await orchestrator.audit(claim)

        print("\n── FINAL AUDIT REPORT ──")
        print(json.dumps(result.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())