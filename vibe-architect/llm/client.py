# llm/client.py

import os
import asyncio
from enum import Enum
from dataclasses import dataclass
from config import LLM_PROVIDER, OLLAMA_MODEL, ANTHROPIC_MODEL, GROQ_API_KEY, GROQ_MODEL

class Provider(Enum):
    OLLAMA    = "ollama"
    ANTHROPIC = "anthropic"
    GROQ      = "groq"

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
            self.model = OLLAMA_MODEL

        elif self.provider == Provider.ANTHROPIC:
            import anthropic
            self._anthropic = anthropic.AsyncAnthropic()
            self.model = ANTHROPIC_MODEL
        
        elif self.provider == Provider.GROQ:
            from groq import AsyncGroq
            self._groq = AsyncGroq(api_key=GROQ_API_KEY)
            self.model = GROQ_MODEL

    async def complete(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        if self.provider == Provider.OLLAMA:
            return await self._ollama_complete(messages, system_prompt, max_tokens)
        if self.provider == Provider.GROQ:
            return await self._groq_complete(messages, system_prompt, max_tokens)
        return await self._anthropic_complete(messages, system_prompt, max_tokens)

    async def _ollama_complete(
        self, messages: list[Message], system_prompt: str, max_tokens: int
    ) -> str:
        formatted = [{"role": "system", "content": system_prompt}]
        formatted += [{"role": m.role, "content": m.content} for m in messages]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
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
        response = await self._anthropic.messages.create(
            model=self.model,
            system=system_prompt,
            messages=formatted,
            max_tokens=max_tokens,
        )
        return response.content[0].text

    
    async def _groq_complete(
    self, messages: list[Message], system_prompt: str, max_tokens: int
) -> str:
        formatted = [{"role": "system", "content": system_prompt}]
        formatted += [{"role": m.role, "content": m.content} for m in messages]
        response = await self._groq.chat.completions.create(
            model=self.model,
            messages=formatted,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content