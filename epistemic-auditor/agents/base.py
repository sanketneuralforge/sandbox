# agents/base.py

import re
import json
from llm.client import LLMClient, Message

class BaseAgent:
    """
    Every agent inherits this. Provides:
    - The tool-calling loop
    - Tool call parsing
    - JSON extraction from responses
    
    Subclasses only need to define:
    - system_prompt
    - tools (a ToolRegistry or None)
    - parse_result(response) -> their specific output model
    """

    MAX_TURNS = 8
    name = "BaseAgent"

    def __init__(self):
        self.llm = LLMClient()

    async def run(self, user_message: str) -> str:
        messages = [Message(role="user", content=user_message)]

        for turn in range(self.MAX_TURNS):
            print(f"  [{self.name}] Turn {turn + 1}")

            response = await self.llm.complete(
                messages=messages,
                system_prompt=self.get_system_prompt(),
            )
            messages.append(Message(role="assistant", content=response))

            # Check for tool call
            tool_call = self._parse_tool_call(response)
            if tool_call and hasattr(self, 'tools') and self.tools:
                tool_name, argument = tool_call

                # ── Turn budget warning ────────────────────────────────
                # When 2 turns remain, stop allowing tool calls and
                # force the agent to synthesize what it already has.
                # This is the key fix for small models that over-search.
                if turn >= self.MAX_TURNS - 2:
                    print(f"  [{self.name}] Turn budget low — forcing synthesis")
                    messages.append(Message(
                        role="user",
                        content=(
                            "You have used most of your available turns. "
                            "Do NOT call any more tools. "
                            "Synthesize what you have found so far and respond "
                            "with FINAL_ANSWER: followed by your JSON immediately."
                        )
                    ))
                    continue

                print(f"  [{self.name}] → {tool_name}({argument[:40]}...)")
                result = self.tools.execute(tool_name, argument)
                messages.append(Message(
                    role="user",
                    content=f"Tool result:\n{result}"
                ))
                continue

            # Check for final answer
            if "FINAL_ANSWER:" in response:
                return response

            # Nudge if neither
            messages.append(Message(
                role="user",
                content="Continue. Call a tool or give FINAL_ANSWER: with your JSON."
            ))

        # Last resort — explicitly ask for output with whatever was gathered
        print(f"  [{self.name}] Max turns reached — extracting best effort response")
        messages.append(Message(
            role="user",
            content=(
                "STOP. You must now respond with FINAL_ANSWER: followed by "
                "your JSON using whatever information you have gathered. "
                "Do not call any more tools. Produce the JSON now."
            )
        ))
        final = await self.llm.complete(
            messages=messages,
            system_prompt=self.get_system_prompt(),
        )
        return final

    def get_system_prompt(self) -> str:
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    def _parse_tool_call(self, response: str):
        match = re.search(
            r'TOOL_CALL:\s*(\w+)\s*\(([^)]+)\)',
            response, re.IGNORECASE
        )
        if match:
            return match.group(1), match.group(2)
        return None

    def _extract_json(self, response: str) -> dict:
        """
        Extracts JSON from a FINAL_ANSWER: response.
        Shared by all agents — every agent returns JSON.
        """
        try:
            after = response.split("FINAL_ANSWER:")[-1].strip()
            cleaned = re.sub(r"```(?:json)?", "", after).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            return json.loads(cleaned[start:end])
        except Exception as e:
            print(f"  [{self.name}] JSON parse failed: {e}")
            return {}