"""
tests/test_gmail_worker.py — Unit tests for workers/gmail_worker.py.

All Gmail API calls are mocked. No real network traffic.
Updated for callback-based threading.Thread API (no PyQt6 signals).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_worker(**overrides):
    from workers.gmail_worker import GmailWorker

    defaults = dict(
        data_dir=Path("/tmp/test_expense_tracker"),
        year=2026,
        month=3,
        label_id=None,
        force_refresh=True,
        custom_rules=[],
    )
    defaults.update(overrides)
    return GmailWorker(**defaults)


# ---------------------------------------------------------------------------
# Callback API tests (replaces old Qt signal tests)
# ---------------------------------------------------------------------------

class TestGmailWorkerCallbacks:
    """Verify that callbacks are invoked correctly."""

    def test_finished_callback(self):
        results = []
        worker = _make_worker(on_finished=results.append)
        worker._dispatch(worker._on_finished, [{"id": "abc", "amount": 100}])
        assert len(results) == 1
        assert results[0][0]["id"] == "abc"

    def test_error_callback(self):
        errors = []
        worker = _make_worker(on_error=errors.append)
        worker._dispatch(worker._on_error, "Gmail API quota exceeded")
        assert "quota" in errors[0].lower()

    def test_progress_callback(self):
        progress_data = []
        worker = _make_worker(on_progress=lambda c, t: progress_data.append((c, t)))
        worker._dispatch(worker._on_progress, 5, 10)
        assert progress_data == [(5, 10)]

    def test_authenticated_callback(self):
        emails = []
        worker = _make_worker(on_authenticated=emails.append)
        worker._dispatch(worker._on_authenticated, "user@example.com")
        assert emails == ["user@example.com"]

    def test_labels_ready_callback(self):
        label_data = []
        worker = _make_worker(on_labels_ready=label_data.append)
        worker._dispatch(worker._on_labels_ready, [{"id": "INBOX", "name": "Inbox"}])
        assert label_data[0][0]["name"] == "Inbox"


# ---------------------------------------------------------------------------
# Abort tests
# ---------------------------------------------------------------------------

class TestGmailWorkerAbort:
    def test_abort_sets_flag(self):
        worker = _make_worker()
        assert worker._abort is False
        worker.abort()
        assert worker._abort is True


# ---------------------------------------------------------------------------
# Query builder tests
# ---------------------------------------------------------------------------

class TestGmailWorkerQueryBuilder:
    def test_query_contains_date_range(self):
        worker = _make_worker(year=2026, month=3)
        query = worker._build_query()
        assert "after:2026/03/01" in query
        assert "before:2026/03/31" in query

    def test_query_contains_expense_keywords(self):
        worker = _make_worker()
        query = worker._build_query()
        for kw in ["receipt", "invoice", "payment", "transaction"]:
            assert kw in query.lower()

    def test_query_excludes_bill_due(self):
        worker = _make_worker()
        query = worker._build_query()
        assert "bill is due" in query.lower()

    def test_february_non_leap(self):
        worker = _make_worker(year=2026, month=2)
        query = worker._build_query()
        assert "before:2026/02/28" in query

    def test_february_leap(self):
        worker = _make_worker(year=2024, month=2)
        query = worker._build_query()
        assert "before:2024/02/29" in query

    def test_december(self):
        worker = _make_worker(year=2026, month=12)
        query = worker._build_query()
        assert "before:2026/12/31" in query


# ---------------------------------------------------------------------------
# _run() integration tests with mocked dependencies
# ---------------------------------------------------------------------------

class TestGmailWorkerRun:
    """Test the full _run() pipeline with mocked Gmail API + DB."""

    def _patch_auth(self):
        """Return a dict of patches for all auth/core imports inside _run()."""
        return {
            "creds":   patch("core.gmail_auth.get_credentials",         return_value=MagicMock()),
            "email":   patch("core.gmail_auth.get_authenticated_email", return_value="test@gmail.com"),
            "labels":  patch("core.gmail_auth.get_gmail_labels",        return_value=[]),
            "service": patch("core.gmail_auth.get_gmail_service"),
        }

    def test_cache_hit_skips_gmail(self):
        """When DB has cached data and force_refresh=False, return cached rows without API calls."""
        cached = [{"id": "c1", "amount": 500}]
        mock_db = MagicMock()
        mock_db.has_month.return_value = True
        mock_db.get_month_expenses.return_value = cached

        finished_rows = []
        worker = _make_worker(force_refresh=False, on_finished=finished_rows.append)

        patches = self._patch_auth()
        with patches["creds"], patches["email"], patches["labels"], patches["service"]:
            with patch("core.db.Database", return_value=mock_db):
                worker._run()

        assert len(finished_rows) == 1
        assert finished_rows[0] == cached

    def test_error_emitted_on_auth_failure(self):
        """Worker calls on_error when auth raises AuthError."""
        from core.gmail_auth import AuthError

        errors = []
        worker = _make_worker(on_error=errors.append)

        with patch("core.gmail_auth.get_credentials", side_effect=AuthError("bad token")):
            worker._run()

        assert len(errors) == 1
        assert "bad token" in errors[0]

    def test_empty_gmail_results(self):
        """Worker calls on_finished([]) when Gmail returns no messages."""
        mock_db = MagicMock()
        mock_db.has_month.return_value = False

        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        finished_rows = []
        worker = _make_worker(on_finished=finished_rows.append)

        patches = self._patch_auth()
        with patches["creds"], patches["email"], patches["labels"]:
            with patch("core.gmail_auth.get_gmail_service", return_value=mock_service):
                with patch("core.db.Database", return_value=mock_db):
                    worker._run()

        assert finished_rows == [[]]

    def test_abort_stops_mid_fetch(self):
        """Worker stops and closes DB when abort() is called before message processing."""
        mock_db = MagicMock()
        mock_db.has_month.return_value = False

        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)],
        }

        finished_rows = []
        worker = _make_worker(on_finished=finished_rows.append)
        worker.abort()   # abort before run

        patches = self._patch_auth()
        with patches["creds"], patches["email"], patches["labels"]:
            with patch("core.gmail_auth.get_gmail_service", return_value=mock_service):
                with patch("core.db.Database", return_value=mock_db):
                    worker._run()

        # Should not emit finished since it was aborted
        assert len(finished_rows) == 0
        mock_db.close.assert_called()

    def test_pagination_collects_all_pages(self):
        """Worker follows nextPageToken to collect messages across pages."""
        mock_db = MagicMock()
        mock_db.has_month.return_value = False
        mock_db.get_ignore_list.return_value = []
        mock_db.upsert_expenses.return_value = 0
        mock_db.get_month_expenses.return_value = []

        page1 = {"messages": [{"id": "p1m1"}], "nextPageToken": "tok2"}
        page2 = {"messages": [{"id": "p2m1"}]}

        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = [page1, page2]
        mock_service.users().messages().get().execute.return_value = {"id": "p1m1"}

        finished_rows = []
        worker = _make_worker(on_finished=finished_rows.append)

        patches = self._patch_auth()
        with patches["creds"], patches["email"], patches["labels"]:
            with patch("core.gmail_auth.get_gmail_service", return_value=mock_service):
                with patch("core.db.Database", return_value=mock_db):
                    with patch("core.expense_parser.parse_gmail_message", return_value=None):
                        with patch("core.deduplicator.find_duplicates", side_effect=lambda x: x):
                            worker._run()

        assert len(finished_rows) == 1


# ---------------------------------------------------------------------------
# AuthOnlyWorker tests
# ---------------------------------------------------------------------------

class TestAuthOnlyWorker:
    def test_callbacks_exist_as_private(self):
        """AuthOnlyWorker exposes callback protocol, not Qt signals."""
        from workers.gmail_worker import AuthOnlyWorker
        worker = AuthOnlyWorker(data_dir=Path("/tmp/test"))
        assert callable(worker._on_authenticated)
        assert callable(worker._on_labels_ready)
        assert callable(worker._on_error)

    def test_callback_called_on_authenticated(self):
        from workers.gmail_worker import AuthOnlyWorker
        emails = []
        worker = AuthOnlyWorker(
            data_dir=Path("/tmp/test"),
            on_authenticated=emails.append,
        )
        worker._dispatch(worker._on_authenticated, "user@test.com")
        assert emails == ["user@test.com"]

    def test_callback_called_on_error(self):
        from workers.gmail_worker import AuthOnlyWorker
        errors = []
        worker = AuthOnlyWorker(
            data_dir=Path("/tmp/test"),
            on_error=errors.append,
        )
        with patch("core.gmail_auth.get_credentials", side_effect=Exception("no creds")):
            worker.run()
        assert len(errors) == 1
        assert "no creds" in errors[0]
