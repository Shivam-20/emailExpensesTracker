"""tests/test_main_window.py — Focused tests for refresh and warning helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main_window import MainWindow


def test_build_fetch_warning_lines_reports_truncation_and_parse_failures() -> None:
    window = MainWindow.__new__(MainWindow)
    window._fetch_stats = {
        "candidate_count": 500,
        "processed_count": 480,
        "parsed_count": 120,
        "no_amount_count": 15,
        "ignored_count": 8,
        "parse_failures": 3,
        "new_rows": 100,
        "truncated": True,
    }

    warnings = window._build_fetch_warning_lines()

    assert any("500 candidate cap" in line for line in warnings)
    assert any("3 email(s) failed" in line for line in warnings)
    assert any("15 candidate email(s) were ignored because no amount was detected" in line for line in warnings)


def test_apply_review_correction_updates_current_rows() -> None:
    window = MainWindow.__new__(MainWindow)
    window._current_rows = [{"id": "m1", "status": "review", "needs_review": 1, "category_edited": None}]

    changed = window._apply_review_correction_to_current_rows("m1", "active", "Travel")

    assert changed is True
    assert window._current_rows[0]["status"] == "active"
    assert window._current_rows[0]["needs_review"] == 0
    assert window._current_rows[0]["category_edited"] == "Travel"