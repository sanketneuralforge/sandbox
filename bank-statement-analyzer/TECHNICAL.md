# Bank Statement Analyzer — Technical Documentation

## Overview

Bank Statement Analyzer is a local-first CLI tool that ingests bank statement files (CSV or PDF), runs an LLM agent to categorize every transaction and detect anomalies, persists everything to a SQLite database, and renders a formatted report both to the terminal and as an HTML file.

The entire pipeline runs locally. No data leaves the machine. The LLM inference is handled by Ollama running `mistral-small` via an OpenAI-compatible API endpoint.

---

## Architecture

```
main.py          CLI entry point — argument parsing, command dispatch
parser.py        File ingestion — CSV and PDF → normalized transaction dicts
database.py      SQLite persistence layer — runs, transactions, categories, anomalies
agent.py         Agentic loop — drives the LLM over batched transactions
tools.py         Tool definitions + executors (categorize, flag, summarize)
reports.py       Report rendering — terminal (rich) + HTML export
config.py        Constants — model name, DB path, batch size, category list
```

All state lives in `bank_analysis.db` (SQLite). There are no external services beyond the local Ollama instance.

---

## Data Flow

```
CSV / PDF file
     │
     ▼
parser.parse_file()
  → returns List[Dict{date, merchant, amount, raw_description}]
     │
     ▼
database.create_run()          → analysis_runs table (run_id)
database.insert_transactions() → transactions table (uncategorized)
     │
     ▼
agent.run_analysis()
  → batches transactions (BATCH_SIZE=10)
  → for each batch: LLM tool-use loop
       ├─ categorize_transactions → database.update_categorization()
       └─ flag_anomaly           → database.flag_anomaly()
  → second pass: generate_summary for each month
     │
     ▼
reports.print_monthly_report()
  → reads aggregates, income, anomalies from DB
  → renders rich tables + panels to terminal
  → saves report_run_<id>.html automatically
```

---

## Module Breakdown

### `config.py`

Central constants. Change the model, batch size, or anomaly threshold here.

| Constant | Value | Purpose |
|---|---|---|
| `MODEL` | `mistral-small` | Ollama model used for inference |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible Ollama endpoint |
| `DB_PATH` | `bank_analysis.db` | SQLite database file path |
| `BATCH_SIZE` | `10` | Transactions per agent invocation |
| `ANOMALY_MULTIPLIER` | `3.0` | Threshold multiplier (informational, detection is LLM-driven) |
| `CATEGORIES` | 10 values | Allowed spending categories enforced via tool schema enum |

Categories: `food`, `rent`, `transport`, `subscriptions`, `utilities`, `healthcare`, `shopping`, `entertainment`, `income`, `other`.

---

### `parser.py`

Handles file ingestion and normalization. Supports two formats.

**CSV parsing (`parse_csv`)**

Uses `pandas.read_csv`. Column detection is fuzzy — it tries to match column names against known aliases (e.g. `"date"`, `"transaction date"`, `"trans date"`). If auto-detection fails, it falls back to interactive prompts asking the user to name the columns manually.

Amount handling supports two layouts:
- **Single amount column** — positive values are income, negative are expenses.
- **Split debit/credit columns** — computes `amount = credit - debit`.

**PDF parsing (`parse_pdf`)**

Uses `pdfplumber` to extract tables from each page. Converts table rows into a DataFrame and then applies the same column-detection and normalization logic as CSV. Only works with digitally-generated PDFs (not scanned images).

**Output shape** (both formats):
```python
{
    "date": "YYYY-MM-DD",
    "merchant": str,
    "amount": float,       # positive = income, negative = expense
    "raw_description": str
}
```

---

### `database.py`

Thin SQLite wrapper using the standard library `sqlite3`. All connections use `row_factory = sqlite3.Row` so rows behave like dicts.

**Schema**

```sql
CREATE TABLE analysis_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    imported_at TEXT NOT NULL         -- ISO-8601 timestamp
);

CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    date            TEXT NOT NULL,    -- YYYY-MM-DD
    merchant        TEXT NOT NULL,
    amount          REAL NOT NULL,    -- negative = expense
    raw_description TEXT,
    category        TEXT,             -- NULL until agent runs
    is_anomaly      INTEGER DEFAULT 0,
    anomaly_reason  TEXT,
    FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
);
```

Each import creates a new `analysis_runs` row. All transactions for that import are linked via `run_id`. This allows multiple imports of different statements without data collision.

**Key query — monthly aggregates:**
```sql
SELECT strftime('%Y-%m', date) as month, category, SUM(amount) as total
FROM transactions
WHERE run_id = ? AND amount < 0
GROUP BY month, category
```
Filters `amount < 0` to exclude income from the expense breakdown.

---

### `tools.py`

Defines the three tool schemas exposed to the LLM, and the executor functions that handle tool call results.

**Tool: `categorize_transactions`**

Accepts a batch of `{id, category, reasoning}` objects. Category is constrained to the `CATEGORIES` enum in the JSON schema, preventing the model from inventing new categories. Each call writes to the DB immediately via `database.update_categorization()`.

**Tool: `flag_anomaly`**

Takes a single `{id, reason}`. Marks the transaction `is_anomaly=1` in the DB with the model's reasoning text.

**Tool: `generate_summary`**

Takes `{month, summary}`. Stores the narrative string in a module-level `_summaries` dict (in-memory). Summaries are not persisted to the DB — they are regenerated on each run and passed directly to the report renderer.

The executor is a simple dispatch function:
```python
def execute_tool(name, inputs) -> str:
    # routes to _exec_categorize / _exec_flag_anomaly / _exec_generate_summary
```
Return values are plain strings fed back to the model as tool result messages.

---

### `agent.py`

Drives the LLM using the OpenAI SDK pointed at Ollama (`base_url=http://localhost:11434/v1`, `api_key="ollama"`).

**Tool-use loop (`_run_tool_loop`)**

Standard agentic loop:
1. Send messages to the model.
2. If `finish_reason == "tool_calls"`, parse each tool call, execute it, append the result as a `role: tool` message.
3. Repeat until `finish_reason` is not `"tool_calls"`.

**Batching**

Transactions are split into chunks of `BATCH_SIZE` (default 10). Each batch gets its own fresh message list with the system prompt prepended. This keeps context windows manageable and avoids the model losing track of earlier transactions in large statements.

**Two-pass design**

1. **Pass 1 — categorization & anomaly detection**: One loop invocation per batch. The model is shown raw transaction lines and asked to call `categorize_transactions` and optionally `flag_anomaly`.

2. **Pass 2 — monthly summaries**: After all batches complete, a single loop is run with the aggregated monthly spending totals. The model is asked to call `generate_summary` once per month.

This separation is intentional: summaries are written after all categorizations are finalized, so they reflect accurate totals.

**System prompt**

```
You are a meticulous financial analyst reviewing bank transactions.
1. Use `categorize_transactions` to assign a category to EVERY transaction.
2. Use `flag_anomaly` for anything suspicious.
3. After categorization, use `generate_summary` to write a concise narrative for each month.
```

The prompt enforces completeness ("EVERY transaction must be categorized").

---

### `reports.py`

Renders output using the `rich` library.

**`print_monthly_report(run_id, summaries, output_path)`**

- Fetches aggregates, income, and anomalies from the DB.
- For each month (sorted chronologically):
  - Renders the AI-generated narrative in a `Panel`.
  - Renders a `Table` of categories sorted by spend descending, with percentage share and a total footer.
  - Appends an income row if present.
- Renders a flagged transactions table at the bottom if anomalies exist.
- If `output_path` is provided, uses a separate `Console(record=True)` to capture all output and calls `console.save_html(output_path)`.

**`print_transaction_list(run_id, month, output_path)`**

Full transaction-level view with date, merchant, amount (color-coded), category, and anomaly flag. Filterable by month. Also supports HTML export.

**HTML export mechanism**

Rich's `Console(record=True)` records all markup rendered to it. `save_html()` produces a self-contained HTML file with inline CSS that mirrors the terminal colors and layout exactly.

---

### `main.py`

CLI built with `argparse`. Three subcommands:

| Command | Description |
|---|---|
| `import --file FILE` | Parse, store, analyze, and auto-save HTML report |
| `report [--run-id N] [--month YYYY-MM] [--transactions] [--output FILE.html]` | Display and optionally export a stored report |
| `list-runs` | Show all imported runs with transaction counts |

The `import` command automatically saves the report to `report_run_<id>.html` without requiring `--output`.

**Duplicate import guard**: Before importing, `find_run_by_filename` checks if the same filename was already imported. If so, the user is warned and import is blocked unless `--force` is passed.

---

## Design Decisions

**Why Ollama / local LLM?**
All financial data stays on the user's machine. No API keys, no cloud costs, no data sent to third parties.

**Why tool-use instead of free-form text parsing?**
Tool-use with a strict enum for categories eliminates the need to parse LLM output. The model calls structured functions; the executor writes directly to the DB. There is no regex or post-processing step.

**Why batch the transactions?**
Local models have smaller effective context windows than cloud models. Batches of 10 keep each prompt short and focused, improving reliability and reducing the chance of the model skipping transactions.

**Why two passes (categorize then summarize)?**
Summaries reference category totals. If summaries were generated mid-stream, they would reflect incomplete data. Running them after all categorizations are committed to the DB ensures accuracy.

**Why SQLite?**
Zero infrastructure. The DB is a single file. Multiple runs of the tool accumulate history without any setup.

**Why Rich for output?**
Rich produces structured, color-coded terminal output with tables and panels. Its `Console(record=True)` + `save_html()` gives HTML export for free with no additional templating code.
