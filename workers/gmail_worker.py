"""
workers/gmail_worker.py — QThread for fetching, parsing, deduplicating, and caching expenses.

Signals
-------
progress(int, int)  current_count, total_count
status(str)         human-readable status message
finished(list)      list of row dicts (sqlite3.Row or plain dict)
error(str)          error message
authenticated(str)  emitted with email address after successful auth
labels_ready(list)  emitted with [{id, name}] label list after auth
"""

import calendar
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

MAX_MESSAGES = 500


class GmailWorker(QThread):
    """
    Background thread: authenticate → check cache → fetch Gmail → parse →
    deduplicate → save to SQLite → emit rows.
    """

    progress      = pyqtSignal(int, int)   # (current, total)
    status        = pyqtSignal(str)
    finished      = pyqtSignal(list)
    error         = pyqtSignal(str)
    authenticated = pyqtSignal(str)        # email address
    labels_ready  = pyqtSignal(list)       # list[dict]

    def __init__(
        self,
        data_dir: Path,
        year: int,
        month: int,
        label_id: Optional[str] = None,
        force_refresh: bool = False,
        custom_rules: Optional[list[dict]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.data_dir      = data_dir
        self.year          = year
        self.month         = month
        self.label_id      = label_id
        self.force_refresh = force_refresh
        self.custom_rules  = custom_rules or []
        self._abort        = False

    def abort(self) -> None:
        self._abort = True

    # ── Thread entry ──────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:
            logger.exception("GmailWorker error")
            self.error.emit(f"Unexpected error: {exc}")

    def _run(self) -> None:
        from core.gmail_auth import (
            get_credentials, get_gmail_service,
            get_authenticated_email, get_gmail_labels, AuthError,
        )
        from core.db import Database
        from core.expense_parser import parse_gmail_message
        from core.deduplicator import find_duplicates

        # ── Auth ──────────────────────────────────────────────────────────
        self.status.emit("🔑 Authenticating…")
        try:
            creds   = get_credentials(self.data_dir)
            email   = get_authenticated_email(self.data_dir)
            self.authenticated.emit(email)
            labels  = get_gmail_labels(self.data_dir)
            self.labels_ready.emit(labels)
        except AuthError as exc:
            self.error.emit(str(exc))
            return

        service = get_gmail_service(self.data_dir, creds)
        month_str = f"{self.year}-{self.month:02d}"

        # ── Cache check ───────────────────────────────────────────────────
        db = Database(self.data_dir)
        db.connect()

        if not self.force_refresh and db.has_month(month_str):
            self.status.emit(f"📦 Loading from cache: {month_str}…")
            rows = db.get_month_expenses(month_str)
            db.close()
            self.finished.emit([dict(r) for r in rows])
            self.status.emit(f"✅ Loaded {len(rows)} expense(s) from cache.")
            self.progress.emit(len(rows), len(rows))
            return

        # ── Gmail fetch ───────────────────────────────────────────────────
        query = self._build_query()
        self.status.emit(f"🔍 Searching Gmail for {calendar.month_name[self.month]} {self.year}…")
        self.progress.emit(0, 1)

        msg_ids: list[str] = []
        page_token: Optional[str] = None

        while True:
            if self._abort:
                db.close()
                return

            kwargs: dict = {"userId": "me", "q": query, "maxResults": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            if self.label_id:
                kwargs["labelIds"] = [self.label_id]

            result = service.users().messages().list(**kwargs).execute()
            msgs   = result.get("messages", [])
            msg_ids.extend(m["id"] for m in msgs)

            page_token = result.get("nextPageToken")
            if not page_token or len(msg_ids) >= MAX_MESSAGES:
                break

        total = len(msg_ids)
        self.status.emit(f"📬 Found {total} candidate email(s) — parsing…")

        if total == 0:
            db.close()
            self.finished.emit([])
            self.status.emit("✅ No expense emails found.")
            self.progress.emit(0, 0)
            return

        # Get ignore list once
        ignore_rows = db.get_ignore_list()
        ignore_senders  = {r["value"] for r in ignore_rows if r["type"] == "sender"}
        ignore_subjects = {r["value"] for r in ignore_rows if r["type"] == "subject"}

        parsed: list[dict] = []

        for idx, msg_id in enumerate(msg_ids[:MAX_MESSAGES]):
            if self._abort:
                db.close()
                return

            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                row = parse_gmail_message(msg, self.custom_rules)
                if row is None:
                    self.progress.emit(idx + 1, total)
                    continue

                # Check ignore list
                sender_l  = row["sender"].lower() + " " + row["sender_email"].lower()
                subject_l = row["subject"].lower()
                if any(ig in sender_l  for ig in ignore_senders):
                    self.progress.emit(idx + 1, total)
                    continue
                if any(ig in subject_l for ig in ignore_subjects):
                    self.progress.emit(idx + 1, total)
                    continue

                row["month"] = month_str
                parsed.append(row)

            except Exception as exc:
                logger.warning("Failed to parse message %s: %s", msg_id, exc)

            self.progress.emit(idx + 1, total)
            self.status.emit(
                f"📧 {idx + 1}/{total} — {len(parsed)} expense(s) found…"
            )

        # ── Deduplication ─────────────────────────────────────────────────
        self.status.emit("🔍 Detecting duplicates…")
        parsed = find_duplicates(parsed)

        # ── Persist ───────────────────────────────────────────────────────
        self.status.emit("💾 Saving to cache…")
        inserted = db.upsert_expenses(parsed)
        rows = db.get_month_expenses(month_str)
        db.close()

        self.progress.emit(total, total)
        self.status.emit(
            f"✅ {len(rows)} expense(s) — "
            f"{calendar.month_name[self.month]} {self.year} "
            f"({inserted} new)."
        )
        self.finished.emit([dict(r) for r in rows])

    # ── Query builder ─────────────────────────────────────────────────────────

    def _build_query(self) -> str:
        last_day = calendar.monthrange(self.year, self.month)[1]
        after    = f"{self.year}/{self.month:02d}/01"
        before   = f"{self.year}/{self.month:02d}/{last_day}"
        keywords = (
            "receipt OR invoice OR payment OR order OR transaction OR "
            "bill OR charged OR booking OR subscription OR debit OR purchase"
        )
        exclude = '-subject:("bill is due" OR "bill due" OR "payment is due" OR "payment due date")'
        return f"subject:({keywords}) {exclude} after:{after} before:{before}"


class AuthOnlyWorker(QThread):
    """Lightweight worker that only authenticates and fetches labels."""

    authenticated = pyqtSignal(str)
    labels_ready  = pyqtSignal(list)
    error         = pyqtSignal(str)

    def __init__(self, data_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.data_dir = data_dir

    def run(self) -> None:
        try:
            from core.gmail_auth import (
                get_credentials, get_authenticated_email,
                get_gmail_labels, AuthError,
            )
            get_credentials(self.data_dir)
            email  = get_authenticated_email(self.data_dir)
            labels = get_gmail_labels(self.data_dir)
            self.authenticated.emit(email)
            self.labels_ready.emit(labels)
        except Exception as exc:
            self.error.emit(str(exc))
