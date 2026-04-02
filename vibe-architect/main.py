# main.py

import asyncio
import json
from agent.core import VibeArchitect

async def main():
    agent = VibeArchitect()

    vibes = [
        "The last hour of a road trip as the sun sets over the highway",
        "Studying alone in a library at 2am, slightly anxious but focused",
    ]

    for vibe in vibes:
        print("\n" + "=" * 60)
        print(f"Vibe: {vibe}")
        print("=" * 60)

        package = await agent.create(vibe)

        print("\n── EMOTIONAL ANCHOR ──")
        print(f"Core feeling: {package.emotional_anchor.core_feeling}")
        print(f"Energy: {package.emotional_anchor.energy:.1f} | "
              f"Warmth: {package.emotional_anchor.warmth:.1f} | "
              f"Tension: {package.emotional_anchor.tension:.1f} | "
              f"Nostalgia: {package.emotional_anchor.nostalgia:.1f}")
        print(f"Tempo: {package.emotional_anchor.musical_tempo}")
        print(f"Key imagery: {', '.join(package.emotional_anchor.key_imagery)}")

        print("\n── MUSIC ──")
        for t in package.music:
            print(f"  {t.artist} — {t.title}")

        print("\n── COLORS ──")
        for c in package.colors:
            print(f"  {c.hex}  {c.name} — {c.feeling}")

        print("\n── FILMS ──")
        for f in package.films:
            print(f"  {f.title} ({f.year}) dir. {f.director}")

        print("\n── POEM ──")
        print(package.poem)

if __name__ == "__main__":
    asyncio.run(main())