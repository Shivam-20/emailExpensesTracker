"""tests/test_review_queue_tab.py — Focused tests for correction callback behavior."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from tabs.review_queue_tab import ReviewQueueTab


def test_save_correction_emits_category_for_expense() -> None:
    tab = ReviewQueueTab.__new__(ReviewQueueTab)
    tab._editing_row_id = "m1"
    tab._db = MagicMock()
    tab._all_rows = [{
        "id": "m1",
        "subject": "Invoice",
        "sender_email": "billing@example.com",
        "status": "review",
    }]
    tab._label_combo = MagicMock()
    tab._label_combo.get.return_value = "EXPENSE"
    tab._cat_combo = MagicMock()
    tab._cat_combo.get.return_value = "Travel"
    tab._hide_action_panel = MagicMock()
    tab._rebuild_chips = MagicMock()
    tab._apply_filters = MagicMock()

    corrected = []
    tab.on_corrected = lambda msg_id, status, category=None: corrected.append((msg_id, status, category))

    tab._save_correction()

    assert corrected == [("m1", "active", "Travel")]
    tab._db.set_expense_status.assert_called_once_with("m1", "active")
    tab._db.set_expense_category.assert_called_once_with("m1", "Travel")


def test_save_correction_omits_category_for_not_expense() -> None:
    tab = ReviewQueueTab.__new__(ReviewQueueTab)
    tab._editing_row_id = "m1"
    tab._db = MagicMock()
    tab._all_rows = [{
        "id": "m1",
        "subject": "Newsletter",
        "sender_email": "noreply@example.com",
        "status": "review",
    }]
    tab._label_combo = MagicMock()
    tab._label_combo.get.return_value = "NOT_EXPENSE"
    tab._cat_combo = MagicMock()
    tab._cat_combo.get.return_value = "Other"
    tab._hide_action_panel = MagicMock()
    tab._rebuild_chips = MagicMock()
    tab._apply_filters = MagicMock()

    corrected = []
    tab.on_corrected = lambda msg_id, status, category=None: corrected.append((msg_id, status, category))

    tab._save_correction()

    assert corrected == [("m1", "excluded", None)]
    tab._db.set_expense_status.assert_called_once_with("m1", "excluded")
    tab._db.set_expense_category.assert_not_called()