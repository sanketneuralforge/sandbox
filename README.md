# Bank Statement Analyzer

A local CLI tool that analyzes bank statements using a local LLM. Import a CSV or PDF statement, and the tool categorizes every transaction, flags anomalies, generates a monthly narrative, and saves the report as an HTML file — all on your machine, no data sent anywhere.

---

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com) running locally with `mistral-small` pulled

---

## Setup

**1. Install Ollama and pull the model**

```bash
# Install Ollama from https://ollama.com, then:
ollama pull mistral-small
```

**2. Clone and install Python dependencies**

```bash
git clone <repo-url>
cd bank-statement-analyzer
pip install -r requirements.txt
```

For PDF support, `pdfplumber` is already in `requirements.txt`. No extra steps needed.

---

## Usage

### Import a statement

```bash
python main.py import --file statement.csv
```

This will:
- Parse the file
- Run the LLM agent to categorize transactions and detect anomalies
- Print a formatted report to the terminal
- Automatically save the report as `report_run_<id>.html`

Re-importing the same filename is blocked by default:

```bash
python main.py import --file statement.csv --force   # override the duplicate check
```

### View a saved report

```bash
python main.py report                        # latest run
python main.py report --run-id 2             # specific run
python main.py report --run-id 2 --month 2024-01   # filter to one month
```

Export any report to HTML manually:

```bash
python main.py report --output my_report.html
```

### View full transaction list

```bash
python main.py report --transactions                  # all transactions, latest run
python main.py report --transactions --month 2024-02  # filter by month
python main.py report --transactions --output txns.html
```

### List all runs

```bash
python main.py list-runs
```

---

## Supported File Formats

**CSV** — The parser auto-detects common column names:

| Field | Recognized column names |
|---|---|
| Date | `date`, `transaction date`, `trans date`, `posted date`, `posting date` |
| Merchant | `description`, `merchant`, `name`, `payee`, `memo` |
| Amount | `amount`, `transaction amount` |
| Debit/Credit | `debit`/`credit`, `withdrawal`/`deposit` |

If auto-detection fails, the tool will prompt you to enter column names manually.

**PDF** — Works with digitally-generated PDFs that contain embedded tables. Scanned/image PDFs are not supported.

### Sample CSV format

```csv
Date,Description,Amount
2024-01-02,SALARY DEPOSIT,5000.00
2024-01-03,WHOLE FOODS MARKET,-67.43
2024-01-05,NETFLIX,-15.99
```

A `sample_statement.csv` is included for testing.

---

## Output

The report includes:

- **Monthly narrative** — a 2-3 sentence AI-generated summary of spending patterns per month
- **Spending breakdown** — table of categories sorted by spend, with percentage share
- **Income** — total deposits per month
- **Flagged transactions** — anything the model identified as unusual (duplicates, large amounts, unexpected charges)

HTML reports are saved automatically on import as `report_run_<id>.html` in the working directory.

---

## Configuration

Edit `config.py` to change defaults:

```python
MODEL = "mistral-small"              # any model available in Ollama
OLLAMA_BASE_URL = "http://localhost:11434/v1"
DB_PATH = "bank_analysis.db"
BATCH_SIZE = 10                      # transactions per LLM call
ANOMALY_MULTIPLIER = 3.0
```

**To use a different model:**

```bash
ollama pull llama3
# then set MODEL = "llama3" in config.py
```

---

## Data & Privacy

Everything runs locally:
- Transactions are stored in `bank_analysis.db` (SQLite) in the project directory
- LLM inference runs via Ollama on `localhost`
- No data is sent to any external service

---

## Troubleshooting

**`Connection refused` on import**
Ollama is not running. Start it with `ollama serve`.

**`model not found` error**
The model hasn't been pulled. Run `ollama pull mistral-small`.

**PDF shows "No tables found"**
The PDF is likely a scanned image. Only digitally-generated PDFs with embedded table data are supported.

**Columns not detected in CSV**
The tool will interactively ask you to enter column names. Alternatively, rename the columns in your CSV to match the recognized names listed above.
