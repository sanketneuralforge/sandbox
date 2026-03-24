# llm/client.py

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional

# ── provider selection ────────────────────────────────────────────
class Provider(Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"

# Change this ONE line to switch providers
ACTIVE_PROVIDER = Provider.OLLAMA

# ── message format (same structure both providers understand) ─────
@dataclass
class Message:
    role: str      # "user" or "assistant"
    content: str

# ── the unified client ────────────────────────────────────────────
class LLMClient:
    """
    One class. Two providers. Identical interface.
    
    Usage:
        client = LLMClient()
        response = await client.complete(messages, system_prompt)
    """

    def __init__(self):
        self.provider = ACTIVE_PROVIDER

        if self.provider == Provider.OLLAMA:
            import ollama
            self._ollama = ollama
            self.model = "mistral-small"   # change to any ollama model

        elif self.provider == Provider.ANTHROPIC:
            import anthropic
            # Reads ANTHROPIC_API_KEY from environment automatically
            self._anthropic = anthropic.Anthropic()
            self.model = "claude-haiku-4-5-20251001"  # cheapest Anthropic model

    async def complete(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        """
        Send messages to whichever provider is active.
        Always returns a plain string — the model's response.
        """
        if self.provider == Provider.OLLAMA:
            return await self._ollama_complete(messages, system_prompt, max_tokens)
        elif self.provider == Provider.ANTHROPIC:
            return await self._anthropic_complete(messages, system_prompt, max_tokens)

    # ── Ollama implementation ──────────────────────────────────────
    async def _ollama_complete(
        self, messages: list[Message], system_prompt: str, max_tokens: int
    ) -> str:
        # Ollama expects messages as dicts with role + content
        formatted = [{"role": "system", "content": system_prompt}]
        formatted += [{"role": m.role, "content": m.content} for m in messages]

        # ollama.chat is synchronous, so we call it directly
        # (we'll make this properly async in Stage 7)
        response = self._ollama.chat(
            model=self.model,
            messages=formatted,
            options={"num_predict": max_tokens},
        )
        return response["message"]["content"]

    # ── Anthropic implementation ───────────────────────────────────
    async def _anthropic_complete(
        self, messages: list[Message], system_prompt: str, max_tokens: int
    ) -> str:
        # Anthropic takes system separately from messages
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        response = self._anthropic.messages.create(
            model=self.model,
            system=system_prompt,
            messages=formatted,
            max_tokens=max_tokens,
        )
        return response.content[0].text