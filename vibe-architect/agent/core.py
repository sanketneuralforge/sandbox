# agent/core.py

import json
import re
from llm.client import LLMClient, Message
from tools.search import WebSearchTool
from agent.prompts import VIBE_ARCHITECT_PROMPT, TOOL_DESCRIPTIONS
from models import VibePackage, EmotionalAnchor, Track, ColorSwatch, Film
from logger import get_logger

log = get_logger("vibe_agent")

class VibeArchitect:
    """
    Single agent that produces a complete VibePackage.
    
    Stage 2: one agent does all four creative tasks.
    Stage 4: splits into EmotionAnalyst, MusicCurator,
             ColorPsychologist, FilmCritic, Poet, CoherenceJudge.
    
    The output schema stays identical — only the producer changes.
    """

    MAX_TURNS = 8

    def __init__(self):
        self.llm    = LLMClient()
        self.search = WebSearchTool()

    async def create(self, vibe: str) -> VibePackage:
        """
        Takes a vibe description and returns a complete VibePackage.
        This is the entry point for all stages.
        """
        log.info(f"Creating vibe package for: '{vibe[:60]}'")
        print(f"\n[VibeArchitect] Processing: '{vibe[:60]}'")

        system_prompt = VIBE_ARCHITECT_PROMPT.format(
            tool_descriptions=TOOL_DESCRIPTIONS
        )

        messages = [
            Message(
                role="user",
                content=f'Create a complete vibe package for this feeling: "{vibe}"'
            )
        ]

        for turn in range(self.MAX_TURNS):
            print(f"  [Agent] Turn {turn + 1}/{self.MAX_TURNS}")

            response = await self.llm.complete(
                messages=messages,
                system_prompt=system_prompt,
            )
            messages.append(Message(role="assistant", content=response))

            # ── Tool call? ─────────────────────────────────────────
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_name, query = tool_call

                if turn >= self.MAX_TURNS - 2:
                    print(f"  [Agent] Turn budget low — forcing final answer")
                    messages.append(Message(
                        role="user",
                        content=(
                            "You have enough material. Do NOT search again. "
                            "Produce your FINAL_ANSWER: with the complete JSON now."
                        )
                    ))
                    continue

                print(f"  [Agent] Searching: {query[:50]}...")
                results = self.search.run(query.strip('"'))
                formatted = self.search.format_for_prompt(results)
                messages.append(Message(
                    role="user",
                    content=f"Search results:\n{formatted}"
                ))
                continue

            # ── Final answer? ──────────────────────────────────────
            if "FINAL_ANSWER:" in response:
                package = self._parse_output(response, vibe)
                log.info(
                    f"Package created: {len(package.music)} tracks, "
                    f"{len(package.colors)} colors, "
                    f"{len(package.films)} films"
                )
                return package

            # ── Neither — nudge ────────────────────────────────────
            messages.append(Message(
                role="user",
                content=(
                    "Continue. Search for more material or produce "
                    "your FINAL_ANSWER: with the complete JSON."
                )
            ))

        # ── Max turns — force final answer ────────────────────────
        print("  [Agent] Max turns reached — requesting final answer")
        messages.append(Message(
            role="user",
            content=(
                "STOP searching. You must now produce FINAL_ANSWER: "
                "with your complete JSON using what you have gathered."
            )
        ))
        final = await self.llm.complete(
            messages=messages,
            system_prompt=system_prompt,
        )
        return self._parse_output(final, vibe)

    def _parse_tool_call(self, response: str):
        match = re.search(
            r'TOOL_CALL:\s*web_search\s*\(([^)]+)\)',
            response, re.IGNORECASE
        )
        if match:
            return "web_search", match.group(1)
        return None

    def _parse_output(self, raw: str, vibe: str) -> VibePackage:
        """
        Extracts and validates the VibePackage from the LLM response.
        
        Production gotcha: creative LLMs are even more prone than
        factual LLMs to adding prose before/after JSON, using markdown
        fences, and producing slightly malformed JSON. Be aggressive
        about cleaning.
        """
        try:
            after = raw.split("FINAL_ANSWER:")[-1].strip()
            cleaned = re.sub(r"```(?:json)?", "", after).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")

            data = json.loads(cleaned[start:end])

            # Parse nested models with safe fallbacks
            anchor_data = data.get("emotional_anchor", {})
            anchor = EmotionalAnchor(
                core_feeling=anchor_data.get("core_feeling", "undefined"),
                energy=float(anchor_data.get("energy", 0.5)),
                warmth=float(anchor_data.get("warmth", 0.5)),
                tension=float(anchor_data.get("tension", 0.5)),
                nostalgia=float(anchor_data.get("nostalgia", 0.5)),
                primary_colors=anchor_data.get("primary_colors", []),
                musical_tempo=anchor_data.get("musical_tempo", "medium"),
                key_imagery=anchor_data.get("key_imagery", []),
            )

            music = [
                Track(
                    title=t.get("title", ""),
                    artist=t.get("artist", ""),
                    reason=t.get("reason", ""),
                )
                for t in data.get("music", [])
            ]

            colors = [
                ColorSwatch(
                    name=c.get("name", ""),
                    hex=c.get("hex", "#888888"),
                    feeling=c.get("feeling", ""),
                )
                for c in data.get("colors", [])
            ]

            films = [
                Film(
                    title=f.get("title", ""),
                    year=int(f.get("year", 2000)),
                    director=f.get("director", ""),
                    reason=f.get("reason", ""),
                )
                for f in data.get("films", [])
            ]

            return VibePackage(
                vibe_input=data.get("vibe_input", vibe),
                emotional_anchor=anchor,
                music=music,
                colors=colors,
                films=films,
                poem=data.get("poem", ""),
            )

        except Exception as e:
            log.error(f"Output parse failed: {e}")
            log.error(f"Raw response preview: {raw[:300]}")
            return self._fallback(vibe)

    def _fallback(self, vibe: str) -> VibePackage:
        """Safe fallback when parsing fails completely."""
        return VibePackage(
            vibe_input=vibe,
            emotional_anchor=EmotionalAnchor(
                core_feeling="undefined",
                energy=0.5, warmth=0.5,
                tension=0.5, nostalgia=0.5,
                primary_colors=[], musical_tempo="medium",
                key_imagery=[],
            ),
            music=[], colors=[], films=[],
            poem="The vibe could not be captured at this time.",
        )