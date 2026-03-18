import os
import pandas as pd
from dateutil import parser as dateparser
from typing import List, Dict, Optional


COMMON_DATE_COLS = ["date", "transaction date", "trans date", "posted date", "posting date"]
COMMON_DESC_COLS = ["description", "merchant", "name", "payee", "transaction description", "memo"]
COMMON_AMOUNT_COLS = ["amount", "transaction amount"]
DEBIT_COLS = ["debit", "withdrawal", "withdrawals"]
CREDIT_COLS = ["credit", "deposit", "deposits"]


def _normalize_col(name: str) -> str:
    return name.strip().lower()


def _find_col(columns: List[str], candidates: List[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _parse_amount(val) -> float:
    if pd.isna(val):
        return 0.0
    return float(str(val).replace(",", "").replace("$", "").strip())


def _normalize_rows(
    df: pd.DataFrame,
    date_col: str,
    desc_col: str,
    amount_col: Optional[str] = None,
    debit_col: Optional[str] = None,
    credit_col: Optional[str] = None,
) -> List[Dict]:
    transactions = []
    for _, row in df.iterrows():
        try:
            date = dateparser.parse(str(row[date_col])).strftime("%Y-%m-%d")
        except Exception:
            continue

        merchant = str(row[desc_col]).strip()

        if amount_col:
            amount = _parse_amount(row[amount_col])
        elif debit_col and credit_col:
            debit = _parse_amount(row.get(debit_col, 0))
            credit = _parse_amount(row.get(credit_col, 0))
            amount = credit - debit  # positive = income, negative = expense
        else:
            continue

        transactions.append({
            "date": date,
            "merchant": merchant,
            "amount": amount,
            "raw_description": merchant,
        })
    return transactions


def parse_csv(filepath: str) -> List[Dict]:
    df = pd.read_csv(filepath)
    cols = df.columns.tolist()

    date_col = _find_col(cols, COMMON_DATE_COLS)
    desc_col = _find_col(cols, COMMON_DESC_COLS)
    amount_col = _find_col(cols, COMMON_AMOUNT_COLS)
    debit_col = _find_col(cols, DEBIT_COLS)
    credit_col = _find_col(cols, CREDIT_COLS)

    if not date_col or not desc_col:
        print(f"\nCould not auto-detect columns. Found: {cols}")
        date_col = input("Enter the date column name: ").strip()
        desc_col = input("Enter the description/merchant column name: ").strip()
        use_single = input("Single amount column? (y/n): ").strip().lower() == "y"
        if use_single:
            amount_col = input("Enter the amount column name: ").strip()
        else:
            debit_col = input("Enter the debit column name: ").strip()
            credit_col = input("Enter the credit column name: ").strip()

    return _normalize_rows(df, date_col, desc_col, amount_col, debit_col, credit_col)


def parse_pdf(filepath: str) -> List[Dict]:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required for PDF parsing. Run: pip install pdfplumber")

    all_rows = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                headers = [str(h).strip() if h else "" for h in table[0]]
                for row in table[1:]:
                    if len(row) != len(headers):
                        continue
                    all_rows.append(dict(zip(headers, row)))

    if not all_rows:
        raise ValueError(
            "No tables found in the PDF. "
            "This tool works with digitally-generated PDFs only (not scanned images)."
        )

    df = pd.DataFrame(all_rows)
    cols = df.columns.tolist()

    date_col = _find_col(cols, COMMON_DATE_COLS)
    desc_col = _find_col(cols, COMMON_DESC_COLS)
    amount_col = _find_col(cols, COMMON_AMOUNT_COLS)
    debit_col = _find_col(cols, DEBIT_COLS)
    credit_col = _find_col(cols, CREDIT_COLS)

    if not date_col or not desc_col:
        print(f"\nCould not auto-detect columns in PDF tables. Found: {cols}")
        date_col = input("Enter the date column name: ").strip()
        desc_col = input("Enter the description/merchant column name: ").strip()
        use_single = input("Single amount column? (y/n): ").strip().lower() == "y"
        if use_single:
            amount_col = input("Enter the amount column name: ").strip()
        else:
            debit_col = input("Enter the debit column name: ").strip()
            credit_col = input("Enter the credit column name: ").strip()

    return _normalize_rows(df, date_col, desc_col, amount_col, debit_col, credit_col)


def parse_file(filepath: str) -> List[Dict]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        transactions = parse_csv(filepath)
    elif ext == ".pdf":
        transactions = parse_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .csv, .pdf")

    if not transactions:
        raise ValueError("No valid transactions found in the file.")

    print(f"  Parsed {len(transactions)} transactions from {os.path.basename(filepath)}")
    return transactions
