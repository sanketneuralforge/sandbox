# agents/base.py — full updated file

import re
import json
from llm.client import LLMClient, Message
from logger import get_logger

log = get_logger("base_agent")

class BaseAgent:

    MAX_TURNS = 6
    name = "BaseAgent"

    def __init__(self):
        self.llm = LLMClient()

    async def run(self, user_message: str, rag_context: str = "") -> str:
        """
        Runs the tool-calling loop.
        
        rag_context: formatted past audits from ChromaDB.
        If provided, prepended to the first user message.
        """
        # ── Inject RAG context into first message ──────────────────
        # We prepend it to the user message, not the system prompt.
        # Why? System prompts are static — RAG context is dynamic
        # and specific to this claim. Keeping them separate makes
        # the system prompt cacheable and the RAG context fresh.
        if rag_context:
            full_message = f"{rag_context}\n\n{'='*50}\n\nNow audit this:\n{user_message}"
        else:
            full_message = user_message

        messages = [Message(role="user", content=full_message)]

        for turn in range(self.MAX_TURNS):
            log.info(f"[{self.name}] Turn {turn + 1}")
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

            if "FINAL_ANSWER:" in response:
                return response

            messages.append(Message(
                role="user",
                content="Continue. Call a tool or give FINAL_ANSWER: with your JSON."
            ))

        # Last resort
        print(f"  [{self.name}] Max turns reached — extracting best effort")
        messages.append(Message(
            role="user",
            content=(
                "STOP. Respond with FINAL_ANSWER: followed by "
                "your JSON using whatever you have gathered. "
                "Do not call any more tools."
            )
        ))
        final = await self.llm.complete(
            messages=messages,
            system_prompt=self.get_system_prompt(),
        )
        return final

    def get_system_prompt(self) -> str:
        raise NotImplementedError

    def _parse_tool_call(self, response: str):
        match = re.search(
            r'TOOL_CALL:\s*(\w+)\s*\(([^)]+)\)',
            response, re.IGNORECASE
        )
        if match:
            return match.group(1), match.group(2)
        return None

    def _extract_json(self, response: str) -> dict:
        try:
            after = response.split("FINAL_ANSWER:")[-1].strip()
            cleaned = re.sub(r"```(?:json)?", "", after).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            return json.loads(cleaned[start:end])
        except Exception as e:
            log.error(f"[{self.name}] JSON parse failed: {e}")
            return {}