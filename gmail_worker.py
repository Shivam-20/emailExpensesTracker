"""
gmail_worker.py — QThread worker that fetches and parses Gmail expense emails.

Signals
-------
progress(int)     0-100 progress percentage
status(str)       human-readable status message shown in the status bar
finished(list)    list[Expense] on success
error(str)        error message string on failure
"""

import calendar
import logging
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from gmail_auth import get_credentials, get_gmail_service, get_authenticated_email, AuthError
from expense_parser import Expense, parse_gmail_message

logger = logging.getLogger(__name__)

# Maximum messages to retrieve per fetch (avoids quota exhaustion)
MAX_MESSAGES = 200


class GmailWorker(QThread):
    """
    Background thread that:
      1. Authenticates with OAuth2
      2. Queries Gmail for expense-related emails in the selected month
      3. Parses each message for monetary amounts + category
      4. Emits results via signals

    Usage
    -----
    worker = GmailWorker(year=2026, month=3)
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    worker.status.connect(status_bar.showMessage)
    worker.start()
    """

    progress = pyqtSignal(int)       # 0-100
    status   = pyqtSignal(str)       # status bar message
    finished = pyqtSignal(list)      # list[Expense]
    error    = pyqtSignal(str)       # error message
    authenticated = pyqtSignal(str)  # emits email address after successful auth

    def __init__(self, year: int, month: int, parent=None) -> None:
        super().__init__(parent)
        self.year  = year
        self.month = month
        self._abort = False

    def abort(self) -> None:
        """Request the worker to stop at the next checkpoint."""
        self._abort = True

    # ── Main thread entry point ───────────────────────────────────────────────

    def run(self) -> None:
        try:
            self._fetch()
        except AuthError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in GmailWorker")
            self.error.emit(f"Unexpected error: {exc}")

    # ── Core fetch logic ──────────────────────────────────────────────────────

    def _fetch(self) -> None:
        self.status.emit("🔑 Authenticating with Gmail…")
        self.progress.emit(5)

        creds = get_credentials()
        email = get_authenticated_email(creds)
        self.authenticated.emit(email)

        service = get_gmail_service(creds)

        query = self._build_query()
        self.status.emit(f"🔍 Searching emails for {calendar.month_name[self.month]} {self.year}…")
        self.progress.emit(15)

        # Collect all message IDs (paginated)
        msg_ids: list[str] = []
        page_token: Optional[str] = None

        while True:
            if self._abort:
                return
            kwargs: dict = {
                "userId": "me",
                "q": query,
                "maxResults": 100,
            }
            if page_token:
                kwargs["pageToken"] = page_token

            result = service.users().messages().list(**kwargs).execute()
            messages = result.get("messages", [])
            msg_ids.extend(m["id"] for m in messages)

            page_token = result.get("nextPageToken")
            if not page_token or len(msg_ids) >= MAX_MESSAGES:
                break

        total = len(msg_ids)
        self.status.emit(f"📬 Found {total} candidate email(s) — parsing…")
        self.progress.emit(20)

        if total == 0:
            self.finished.emit([])
            self.status.emit("✅ Done — no expense emails found.")
            self.progress.emit(100)
            return

        expenses: list[Expense] = []

        for idx, msg_id in enumerate(msg_ids[:MAX_MESSAGES]):
            if self._abort:
                return

            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="full",
                ).execute()

                expense = parse_gmail_message(msg)
                if expense:
                    expenses.append(expense)
            except Exception as exc:
                logger.warning("Failed to parse message %s: %s", msg_id, exc)

            # Emit progress 20→95 over all messages
            pct = 20 + int(75 * (idx + 1) / total)
            self.progress.emit(pct)
            self.status.emit(
                f"📧 Parsing {idx + 1}/{total} — found {len(expenses)} expense(s)…"
            )

        self.progress.emit(100)
        self.status.emit(
            f"✅ Done — {len(expenses)} expense(s) found in "
            f"{calendar.month_name[self.month]} {self.year}."
        )
        self.finished.emit(expenses)

    # ── Query builder ─────────────────────────────────────────────────────────

    def _build_query(self) -> str:
        last_day = calendar.monthrange(self.year, self.month)[1]
        # Gmail date format: YYYY/MM/DD
        after  = f"{self.year}/{self.month:02d}/01"
        before = f"{self.year}/{self.month:02d}/{last_day}"

        keywords = (
            "receipt OR invoice OR payment OR order OR transaction OR "
            "bill OR charged OR booking OR subscription OR debit OR purchase"
        )
        return f"subject:({keywords}) after:{after} before:{before}"
