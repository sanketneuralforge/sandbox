from typing import Dict, Any
import database
from config import CATEGORIES


# ── Tool schemas passed to Claude ────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "categorize_transactions",
            "description": (
                "Assign a spending category to each transaction in the batch. "
                "Call this for every transaction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categorizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "description": "Transaction DB id"},
                                "category": {
                                    "type": "string",
                                    "enum": CATEGORIES,
                                    "description": "Spending category",
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "One-sentence explanation",
                                },
                            },
                            "required": ["id", "category", "reasoning"],
                        },
                    }
                },
                "required": ["categorizations"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_anomaly",
            "description": (
                "Flag a transaction as anomalous — e.g. duplicate charge, "
                "unusually large amount, unexpected subscription price change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Transaction DB id"},
                    "reason": {
                        "type": "string",
                        "description": "Why this transaction is unusual",
                    },
                },
                "required": ["id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_summary",
            "description": "Write a 2-3 sentence narrative summary for a given month's spending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Month in YYYY-MM format",
                    },
                    "summary": {
                        "type": "string",
                        "description": "2-3 sentence narrative of spending patterns for the month",
                    },
                },
                "required": ["month", "summary"],
            },
        },
    },
]


# ── Executor functions ────────────────────────────────────────────────────────

# Summaries are stored in memory (run_id → month → text) during agent execution
_summaries: Dict[str, str] = {}


def execute_tool(name: str, inputs: Dict[str, Any]) -> str:
    if name == "categorize_transactions":
        return _exec_categorize(inputs)
    elif name == "flag_anomaly":
        return _exec_flag_anomaly(inputs)
    elif name == "generate_summary":
        return _exec_generate_summary(inputs)
    else:
        return f"Unknown tool: {name}"


def _exec_categorize(inputs: Dict[str, Any]) -> str:
    categorizations = inputs.get("categorizations", [])
    count = 0
    for item in categorizations:
        tx_id = item.get("id") or item.get("transaction_id")
        category = item.get("category", "other")
        if tx_id:
            database.update_categorization(int(tx_id), category)
            count += 1
    return f"Categorized {count} transactions."


def _exec_flag_anomaly(inputs: Dict[str, Any]) -> str:
    tx_id = inputs.get("id") or inputs.get("transaction_id") or inputs.get("tx_id")
    reason = inputs.get("reason") or inputs.get("anomaly_reason") or "flagged by model"
    if not tx_id:
        return "Skipped: no transaction id provided."
    database.flag_anomaly(int(tx_id), reason)
    return f"Flagged transaction {tx_id} as anomaly."


def _exec_generate_summary(inputs: Dict[str, Any]) -> str:
    _summaries[inputs["month"]] = inputs["summary"]
    return f"Summary recorded for {inputs['month']}."


def get_summaries() -> Dict[str, str]:
    return dict(_summaries)


def clear_summaries():
    _summaries.clear()
