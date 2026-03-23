"""
workers/gmail_worker.py — Background Thread for fetching, parsing, deduplicating, and caching expenses.

Callbacks (passed at construction instead of Qt signals)
-------
on_progress(int, int)   current_count, total_count
on_status(str)          human-readable status message
on_finished(list)       list of row dicts
on_error(str)           error message
on_authenticated(str)   email address after successful auth
on_labels_ready(list)   [{id, name}] label list after auth
"""

import calendar
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

MAX_MESSAGES = 500


def _empty_stats() -> dict[str, int | bool]:
    return {
        "candidate_count": 0,
        "processed_count": 0,
        "parsed_count": 0,
        "no_amount_count": 0,
        "ignored_count": 0,
        "parse_failures": 0,
        "new_rows": 0,
        "truncated": False,
    }


class GmailWorker(threading.Thread):
    """
    Background thread: authenticate → check cache → fetch Gmail → parse →
    deduplicate → save to SQLite → call on_finished.
    """

    def __init__(
        self,
        data_dir: Path,
        year: int,
        month: int,
        label_id: Optional[str] = None,
        force_refresh: bool = False,
        custom_rules: Optional[list[dict]] = None,
        on_progress: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_authenticated: Optional[Callable] = None,
        on_labels_ready: Optional[Callable] = None,
        ui_ref=None,   # CTk root or widget for after() dispatch
    ) -> None:
        super().__init__(daemon=True)
        self.data_dir        = data_dir
        self.year            = year
        self.month           = month
        self.label_id        = label_id
        self.force_refresh   = force_refresh
        self.custom_rules    = custom_rules or []
        self._abort          = False
        self._ui             = ui_ref
        self.stats           = _empty_stats()

        self._on_progress      = on_progress      or (lambda *_: None)
        self._on_status        = on_status        or (lambda *_: None)
        self._on_finished      = on_finished      or (lambda *_: None)
        self._on_error         = on_error         or (lambda *_: None)
        self._on_authenticated = on_authenticated or (lambda *_: None)
        self._on_labels_ready  = on_labels_ready  or (lambda *_: None)

    def abort(self) -> None:
        self._abort = True

    def is_running(self) -> bool:
        return self.is_alive()

    def wait(self, timeout_ms: int = 3000) -> None:
        self.join(timeout=timeout_ms / 1000)

    # ── UI-safe dispatch ──────────────────────────────────────────────────────

    def _dispatch(self, fn: Callable, *args) -> None:
        """Call fn(*args) on the UI thread via widget.after()."""
        if self._ui and self._ui.winfo_exists():
            self._ui.after(0, lambda: fn(*args))
        else:
            fn(*args)

    # ── Thread entry ──────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:
            logger.exception("GmailWorker error")
            self._dispatch(self._on_error, f"Unexpected error: {exc}")

    def _run(self) -> None:
        from core.gmail_auth import (
            get_credentials, get_gmail_service,
            get_authenticated_email, get_gmail_labels, AuthError,
        )
        from core.db import Database
        from core.expense_parser import parse_gmail_message
        from core.deduplicator import find_duplicates

        # ── Auth ──────────────────────────────────────────────────────────
        self._dispatch(self._on_status, "🔑 Authenticating…")
        try:
            creds  = get_credentials(self.data_dir)
            email  = get_authenticated_email(self.data_dir)
            self._dispatch(self._on_authenticated, email)
            labels = get_gmail_labels(self.data_dir)
            self._dispatch(self._on_labels_ready, labels)
        except AuthError as exc:
            self._dispatch(self._on_error, str(exc))
            return

        service   = get_gmail_service(self.data_dir, creds)
        month_str = f"{self.year}-{self.month:02d}"

        # ── Cache check ───────────────────────────────────────────────────
        db = Database(self.data_dir)
        db.connect()

        if not self.force_refresh and db.has_month(month_str):
            self._dispatch(self._on_status, f"📦 Loading from cache: {month_str}…")
            rows = db.get_month_expenses(month_str)
            db.close()
            self._dispatch(self._on_finished, [dict(r) for r in rows])
            self._dispatch(self._on_status, f"✅ Loaded {len(rows)} expense(s) from cache.")
            self._dispatch(self._on_progress, len(rows), len(rows))
            return

        # ── Gmail fetch ───────────────────────────────────────────────────
        query = self._build_query()
        self._dispatch(self._on_status,
                       f"🔍 Searching Gmail for {calendar.month_name[self.month]} {self.year}…")
        self._dispatch(self._on_progress, 0, 1)

        msg_ids: list[str] = []
        page_token: Optional[str] = None
        truncated = False

        while True:
            if self._abort:
                db.close()
                return

            kwargs: dict = {"userId": "me", "q": query, "maxResults": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            if self.label_id:
                kwargs["labelIds"] = [self.label_id]

            result  = service.users().messages().list(**kwargs).execute()
            msgs    = result.get("messages", [])
            msg_ids.extend(m["id"] for m in msgs)

            page_token = result.get("nextPageToken")
            if len(msg_ids) >= MAX_MESSAGES:
                msg_ids = msg_ids[:MAX_MESSAGES]
                truncated = bool(page_token) or len(msgs) > 0
                break
            if not page_token:
                break

        total = len(msg_ids)
        self.stats["candidate_count"] = total
        self.stats["truncated"] = truncated
        self._dispatch(self._on_status,
                       f"📬 Found {total} candidate email(s) — parsing…")

        if total == 0:
            db.close()
            self._dispatch(self._on_finished, [])
            self._dispatch(self._on_status, "✅ No expense emails found.")
            self._dispatch(self._on_progress, 0, 0)
            return

        # Get ignore list once
        ignore_rows     = db.get_ignore_list()
        ignore_senders  = {r["value"] for r in ignore_rows if r["type"] == "sender"}
        ignore_subjects = {r["value"] for r in ignore_rows if r["type"] == "subject"}

        parsed: list[dict] = []

        for idx, msg_id in enumerate(msg_ids):
            if self._abort:
                db.close()
                return

            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                row = parse_gmail_message(msg, self.custom_rules)
                if row is None:
                    self.stats["no_amount_count"] += 1
                    self._dispatch(self._on_progress, idx + 1, total)
                    continue

                sender_l  = row["sender"].lower() + " " + row["sender_email"].lower()
                subject_l = row["subject"].lower()
                if any(ig in sender_l  for ig in ignore_senders):
                    self.stats["ignored_count"] += 1
                    self._dispatch(self._on_progress, idx + 1, total)
                    continue
                if any(ig in subject_l for ig in ignore_subjects):
                    self.stats["ignored_count"] += 1
                    self._dispatch(self._on_progress, idx + 1, total)
                    continue

                row["month"] = month_str
                parsed.append(row)
                self.stats["parsed_count"] = len(parsed)

            except Exception as exc:
                self.stats["parse_failures"] += 1
                logger.warning("Failed to parse message %s: %s", msg_id, exc)

            self.stats["processed_count"] = idx + 1
            self._dispatch(self._on_progress, idx + 1, total)
            self._dispatch(self._on_status,
                           f"📧 {idx + 1}/{total} — {len(parsed)} expense(s) found…")

        # ── Deduplication ─────────────────────────────────────────────────
        self._dispatch(self._on_status, "🔍 Detecting duplicates…")
        parsed = find_duplicates(parsed)

        # ── Persist ───────────────────────────────────────────────────────
        self._dispatch(self._on_status, "💾 Saving to cache…")
        inserted = db.upsert_expenses(parsed)
        self.stats["new_rows"] = inserted
        rows     = db.get_month_expenses(month_str)
        db.close()

        self._dispatch(self._on_progress, total, total)
        self._dispatch(self._on_status,
                       f"✅ {len(rows)} expense(s) — "
                       f"{calendar.month_name[self.month]} {self.year} "
                       f"({inserted} new).")
        self._dispatch(self._on_finished, [dict(r) for r in rows])

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


class AuthOnlyWorker(threading.Thread):
    """Lightweight worker that only authenticates and fetches labels."""

    def __init__(
        self,
        data_dir: Path,
        on_authenticated: Optional[Callable] = None,
        on_labels_ready: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        ui_ref=None,
    ) -> None:
        super().__init__(daemon=True)
        self.data_dir        = data_dir
        self._ui             = ui_ref
        self._on_authenticated = on_authenticated or (lambda *_: None)
        self._on_labels_ready  = on_labels_ready  or (lambda *_: None)
        self._on_error         = on_error         or (lambda *_: None)

    def _dispatch(self, fn: Callable, *args) -> None:
        if self._ui and self._ui.winfo_exists():
            self._ui.after(0, lambda: fn(*args))
        else:
            fn(*args)

    def run(self) -> None:
        try:
            from core.gmail_auth import (
                get_credentials, get_authenticated_email,
                get_gmail_labels, AuthError,
            )
            get_credentials(self.data_dir)
            email  = get_authenticated_email(self.data_dir)
            labels = get_gmail_labels(self.data_dir)
            self._dispatch(self._on_authenticated, email)
            self._dispatch(self._on_labels_ready, labels)
        except Exception as exc:
            self._dispatch(self._on_error, str(exc))
