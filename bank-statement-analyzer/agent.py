import json
from openai import OpenAI
from typing import List, Dict
from rich.progress import Progress, SpinnerColumn, TextColumn

import database
import tools as tool_module
from config import MODEL, BATCH_SIZE, OLLAMA_BASE_URL

SYSTEM_PROMPT = """You are a meticulous financial analyst reviewing bank transactions.

Your job:
1. Use `categorize_transactions` to assign a category to EVERY transaction.
2. Use `flag_anomaly` for anything suspicious: duplicate charges, unusually large amounts,
   unexpected subscription price changes, or anything that warrants attention.
3. After categorization, use `generate_summary` to write a concise narrative for each month.

Be thorough — every transaction must be categorized before you finish."""


def _get_client() -> OpenAI:
    return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def _run_tool_loop(client: OpenAI, messages: List[Dict]) -> List[Dict]:
    """Run the Ollama tool-use loop until the model stops calling tools."""
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tool_module.TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        finish_reason = response.choices[0].finish_reason

        if finish_reason == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result_text = tool_module.execute_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })
        else:
            break

    return messages


def _build_batch_prompt(batch: List[Dict]) -> str:
    lines = ["Categorize these transactions:\n"]
    for tx in batch:
        sign = "+" if tx["amount"] > 0 else ""
        lines.append(
            f"  ID {tx['id']}: {tx['date']} | {tx['merchant']} | {sign}{tx['amount']:.2f}"
        )
    return "\n".join(lines)


def run_analysis(run_id: int, db_transactions: List[Dict]):
    """Main entry point. Runs Ollama agent over all transactions."""
    tool_module.clear_summaries()
    client = _get_client()

    total = len(db_transactions)
    batches = [
        db_transactions[i: i + BATCH_SIZE]
        for i in range(0, total, BATCH_SIZE)
    ]

    print(f"\n  Running agent over {total} transactions in {len(batches)} batches...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Categorizing...", total=len(batches))

        for i, batch in enumerate(batches):
            progress.update(task, description=f"Batch {i + 1}/{len(batches)}...")
            prompt = _build_batch_prompt(batch)
            messages: List[Dict] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            _run_tool_loop(client, messages)
            progress.advance(task)

    _generate_monthly_summaries(client, run_id)

    return tool_module.get_summaries()


def _generate_monthly_summaries(client: OpenAI, run_id: int):
    aggregates = database.get_monthly_aggregates(run_id)
    income = database.get_income(run_id)

    if not aggregates:
        return

    lines = ["Monthly spending aggregates (call generate_summary for each month):\n"]
    for month, cats in sorted(aggregates.items()):
        lines.append(f"\n{month}:")
        for cat, total in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: ${total:.2f}")
        if month in income:
            lines.append(f"  income: +${income[month]:.2f}")

    messages: List[Dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]
    _run_tool_loop(client, messages)
