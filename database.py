import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            raw_description TEXT,
            category TEXT,
            is_anomaly INTEGER DEFAULT 0,
            anomaly_reason TEXT,
            FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
        );
    """)
    conn.commit()
    conn.close()


def create_run(filename: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO analysis_runs (filename, imported_at) VALUES (?, ?)",
        (filename, datetime.now().isoformat())
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id


def find_run_by_filename(filename: str) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_runs WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def insert_transactions(run_id: int, transactions: List[Dict]) -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    ids = []
    for tx in transactions:
        cursor.execute(
            """INSERT INTO transactions (run_id, date, merchant, amount, raw_description)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, tx["date"], tx["merchant"], tx["amount"], tx.get("raw_description", ""))
        )
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids


def update_categorization(tx_id: int, category: str):
    conn = get_connection()
    conn.execute(
        "UPDATE transactions SET category = ? WHERE id = ?",
        (category, tx_id)
    )
    conn.commit()
    conn.close()


def flag_anomaly(tx_id: int, reason: str):
    conn = get_connection()
    conn.execute(
        "UPDATE transactions SET is_anomaly = 1, anomaly_reason = ? WHERE id = ?",
        (reason, tx_id)
    )
    conn.commit()
    conn.close()


def get_transactions(run_id: int) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM transactions WHERE run_id = ? ORDER BY date",
        (run_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_anomalies(run_id: int) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM transactions WHERE run_id = ? AND is_anomaly = 1 ORDER BY date",
        (run_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_monthly_aggregates(run_id: int) -> Dict[str, Dict[str, float]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT strftime('%Y-%m', date) as month, category, SUM(amount) as total
           FROM transactions
           WHERE run_id = ? AND amount < 0
           GROUP BY month, category
           ORDER BY month, category""",
        (run_id,)
    )
    result: Dict[str, Dict[str, float]] = {}
    for row in cursor.fetchall():
        month, cat, total = row["month"], row["category"] or "uncategorized", row["total"]
        result.setdefault(month, {})[cat] = abs(total)
    conn.close()
    return result


def get_income(run_id: int) -> Dict[str, float]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
           FROM transactions
           WHERE run_id = ? AND amount > 0
           GROUP BY month ORDER BY month""",
        (run_id,)
    )
    result = {row["month"]: row["total"] for row in cursor.fetchall()}
    conn.close()
    return result


def list_runs() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, COUNT(t.id) as tx_count
        FROM analysis_runs r
        LEFT JOIN transactions t ON t.run_id = r.id
        GROUP BY r.id ORDER BY r.id DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
