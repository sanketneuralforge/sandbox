# config.py

import os
import dotenv

dotenv.load_dotenv()

LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")