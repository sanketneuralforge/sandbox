# llm/client.py — full updated file

import os
import asyncio
from dataclasses import dataclass
from config import LLM_PROVIDER, OLLAMA_MODEL, ANTHROPIC_MODEL, ANTHROPIC_API_KEY
from enum import Enum

class Provider(Enum):
    OLLAMA    = "ollama"
    ANTHROPIC = "anthropic"

ACTIVE_PROVIDER = Provider(LLM_PROVIDER)

@dataclass
class Message:
    role: str
    content: str

class LLMClient:

    def __init__(self):
        self.provider = ACTIVE_PROVIDER

        if self.provider == Provider.OLLAMA:
            import ollama
            self._ollama = ollama
            self.model = "mistral-small"

        elif self.provider == Provider.ANTHROPIC:
            import anthropic
            self._anthropic = anthropic.Anthropic()
            self.model = "claude-haiku-4-5-20251001"

    async def complete(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        if self.provider == Provider.OLLAMA:
            return await self._ollama_complete(messages, system_prompt, max_tokens)
        elif self.provider == Provider.ANTHROPIC:
            return await self._anthropic_complete(messages, system_prompt, max_tokens)

    async def _ollama_complete(
        self, messages: list[Message], system_prompt: str, max_tokens: int
    ) -> str:
        formatted = [{"role": "system", "content": system_prompt}]
        formatted += [{"role": m.role, "content": m.content} for m in messages]

        # ── Key fix: run sync ollama.chat in a thread pool ─────────
        # This frees the event loop so asyncio.gather() actually
        # runs agents in parallel instead of blocking sequentially.
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,  # uses default ThreadPoolExecutor
            lambda: self._ollama.chat(
                model=self.model,
                messages=formatted,
                options={"num_predict": max_tokens},
            )
        )
        return response["message"]["content"]

    async def _anthropic_complete(
        self, messages: list[Message], system_prompt: str, max_tokens: int
    ) -> str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        # Anthropic SDK has native async — use it directly
        # Switch to AsyncAnthropic for proper async support
        import anthropic
        async_client = anthropic.AsyncAnthropic()
        response = await async_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=formatted,
            max_tokens=max_tokens,
        )
        return response.content[0].text