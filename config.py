import os

MODEL = "mistral-small"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

DB_PATH = "bank_analysis.db"
BATCH_SIZE = 10
ANOMALY_MULTIPLIER = 3.0  # flag if amount > 3x category average

CATEGORIES = [
    "food",
    "rent",
    "transport",
    "subscriptions",
    "utilities",
    "healthcare",
    "shopping",
    "entertainment",
    "income",
    "other",
]
