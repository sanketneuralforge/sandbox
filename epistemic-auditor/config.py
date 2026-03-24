# config.py

import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_PROVIDER              = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL              = os.getenv("OLLAMA_MODEL", "mistral-small")
ANTHROPIC_API_KEY         = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL           = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Gmail
AUDIT_NOTIFICATION_EMAIL  = os.getenv("AUDIT_NOTIFICATION_EMAIL", "")

# Memory
MEMORY_STORAGE_PATH       = os.getenv("MEMORY_STORAGE_PATH", "memory/claim_store.json")
SIMILARITY_THRESHOLD      = float(os.getenv("SIMILARITY_THRESHOLD", "0.92"))

# HITL
HITL_ENABLED              = os.getenv("HITL_ENABLED", "true").lower() == "true"
HITL_CONFIDENCE_THRESHOLD = float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "0.5"))

# Evals
EVAL_USE_LLM_JUDGE        = os.getenv("EVAL_USE_LLM_JUDGE", "true").lower() == "true"