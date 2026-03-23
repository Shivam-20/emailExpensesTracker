"""tests/test_expense_parser.py — Focused tests for parser fallback behavior."""

import base64
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.expense_parser import parse_gmail_message


def _gmail_message(body_text: str = "Invoice paid INR 500") -> dict:
    encoded_body = base64.urlsafe_b64encode(body_text.encode("utf-8")).decode("ascii")
    return {
        "id": "msg-1",
        "snippet": body_text,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Invoice paid"},
                {"name": "From", "value": "Vendor <billing@example.com>"},
                {"name": "Date", "value": "Mon, 01 Mar 2026 10:00:00 +0000"},
            ],
            "body": {"data": encoded_body},
        },
    }


def test_classifier_exception_sends_message_to_review() -> None:
    """Parser should keep the row but flag it for review on classifier failure."""
    with patch("classifier.classify", side_effect=RuntimeError("classifier broke")):
        row = parse_gmail_message(_gmail_message())

    assert row is not None
    assert row["status"] == "review"
    assert row["needs_review"] == 1
    assert row["classification_source"] == "rules_fallback"
    assert row["notes"] == "Classifier fallback triggered; requires review."


def test_import_error_uses_rules_fallback_without_review() -> None:
    """Missing classifier dependency should keep the rule-based row active."""
    with patch("classifier.classify", side_effect=ImportError("missing classifier")):
        row = parse_gmail_message(_gmail_message())

    assert row is not None
    assert row["status"] == "active"
    assert row["needs_review"] == 0
    assert row["classification_source"] == "rules_fallback"