"""
core/db.py — SQLite database schema creation and CRUD helpers.

All operations are synchronous (called from QThread only, not main thread).
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id                    TEXT PRIMARY KEY,
    fetch_date            TEXT,
    email_date            TEXT,
    month                 TEXT,
    sender                TEXT,
    sender_email          TEXT,
    subject               TEXT,
    amount                REAL,
    amount_edited         REAL,
    currency              TEXT DEFAULT 'INR',
    payment_method        TEXT DEFAULT 'Unknown',
    category              TEXT DEFAULT 'Other',
    category_edited       TEXT,
    email_category        TEXT,
    tags                  TEXT DEFAULT '[]',
    confidence            TEXT DEFAULT 'LOW',
    status                TEXT DEFAULT 'active',
    snippet               TEXT,
    notes                 TEXT,
    classification_source TEXT DEFAULT 'rules',
    needs_review          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ignore_list (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type       TEXT,
    value      TEXT,
    created_at TEXT,
    UNIQUE(type, value)
);

CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    amount   REAL DEFAULT 0
);
"""


class Database:
    """Thin wrapper around a SQLite connection for expense data."""

    def __init__(self, data_dir: Path) -> None:
        self.db_path = data_dir / "expenses.db"
        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection management ─────────────────────────────────────────────────

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()
        logger.info("Connected to database: %s", self.db_path)

    def _migrate(self) -> None:
        """Apply incremental schema migrations for existing databases."""
        existing = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(expenses)").fetchall()
        }
        additions = {
            "classification_source": "TEXT DEFAULT 'rules'",
            "needs_review":          "INTEGER DEFAULT 0",
            "email_category":       "TEXT",
        }
        for col, definition in additions.items():
            if col not in existing:
                self._conn.execute(
                    f"ALTER TABLE expenses ADD COLUMN {col} {definition}"
                )
                logger.info("DB migration: added column expenses.%s", col)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected — call connect() first.")
        return self._conn

    # ── Month cache check ─────────────────────────────────────────────────────

    def has_month(self, month: str) -> bool:
        """Return True if any active/excluded rows exist for 'YYYY-MM'."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE month=?", (month,)
        ).fetchone()
        return row[0] > 0

    # ── Expense CRUD ──────────────────────────────────────────────────────────

    def upsert_expenses(self, rows: list[dict]) -> int:
        """
        Insert or replace expense rows. Preserves user-edited fields
        (amount_edited, category_edited, tags, status, notes) if row exists.
        Returns count of newly inserted rows.
        """
        inserted = 0
        for row in rows:
            # Ensure new classifier fields have defaults
            row.setdefault("classification_source", "rules")
            row.setdefault("needs_review", 0)
            row.setdefault("email_category", None)

            existing = self.conn.execute(
                "SELECT amount_edited, category_edited, tags, status, notes, email_category "
                "FROM expenses WHERE id=?", (row["id"],)
            ).fetchone()

            if existing:
                # Preserve user edits
                row["amount_edited"]   = existing["amount_edited"]
                row["category_edited"] = existing["category_edited"]
                row["tags"]            = existing["tags"]
                row["status"]          = existing["status"]
                row["notes"]           = existing["notes"]
                if existing["email_category"]:
                    row["email_category"] = existing["email_category"]
            else:
                inserted += 1

            self.conn.execute("""
                INSERT OR REPLACE INTO expenses
                    (id, fetch_date, email_date, month, sender, sender_email, subject,
                     amount, amount_edited, currency, payment_method,
                     category, category_edited, email_category, tags, confidence, status, snippet, notes,
                     classification_source, needs_review)
                VALUES
                    (:id, :fetch_date, :email_date, :month, :sender, :sender_email, :subject,
                     :amount, :amount_edited, :currency, :payment_method,
                     :category, :category_edited, :email_category, :tags, :confidence, :status, :snippet, :notes,
                     :classification_source, :needs_review)
            """, row)

        self.conn.commit()
        return inserted

    def get_month_expenses(self, month: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM expenses WHERE month=? ORDER BY email_date DESC", (month,)
        ).fetchall()

    def update_expense_field(self, msg_id: str, field: str, value: Any) -> None:
        allowed = {"amount_edited", "category_edited", "tags", "status", "notes"}
        if field not in allowed:
            raise ValueError(f"Field '{field}' is not user-editable.")
        self.conn.execute(
            f"UPDATE expenses SET {field}=? WHERE id=?", (value, msg_id)
        )
        self.conn.commit()

    def delete_month(self, month: str) -> None:
        self.conn.execute("DELETE FROM expenses WHERE month=?", (month,))
        self.conn.commit()

    # ── Multi-month for trends ────────────────────────────────────────────────

    def get_months_expenses(self, months: list[str]) -> list[sqlite3.Row]:
        placeholders = ",".join("?" * len(months))
        return self.conn.execute(
            f"SELECT * FROM expenses WHERE month IN ({placeholders}) "
            f"AND status != 'excluded' ORDER BY email_date",
            months,
        ).fetchall()

    def get_available_months(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT month FROM expenses ORDER BY month"
        ).fetchall()
        return [r[0] for r in rows]

    # ── Ignore list ───────────────────────────────────────────────────────────

    def get_ignore_list(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM ignore_list ORDER BY created_at DESC"
        ).fetchall()

    def add_ignore(self, type_: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                "INSERT INTO ignore_list (type, value, created_at) VALUES (?,?,?)",
                (type_, value.lower(), now),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # already ignored

    def remove_ignore(self, ignore_id: int) -> None:
        self.conn.execute("DELETE FROM ignore_list WHERE id=?", (ignore_id,))
        self.conn.commit()

    def is_ignored(self, sender: str, subject: str) -> bool:
        rows = self.get_ignore_list()
        sender_l  = sender.lower()
        subject_l = subject.lower()
        for row in rows:
            if row["type"] == "sender"  and row["value"] in sender_l:
                return True
            if row["type"] == "subject" and row["value"] in subject_l:
                return True
        return False

    # ── Budgets ───────────────────────────────────────────────────────────────

    def get_budgets(self) -> dict[str, float]:
        rows = self.conn.execute("SELECT category, amount FROM budgets").fetchall()
        return {r["category"]: r["amount"] for r in rows}

    def set_budget(self, category: str, amount: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO budgets (category, amount) VALUES (?,?)",
            (category, amount),
        )
        self.conn.commit()

    # ── Email category analytics ───────────────────────────────────────────────

    def get_all_expenses(self) -> list[sqlite3.Row]:
        """Return all non-excluded expenses."""
        return self.conn.execute(
            "SELECT * FROM expenses WHERE status != 'excluded' ORDER BY email_date DESC"
        ).fetchall()
