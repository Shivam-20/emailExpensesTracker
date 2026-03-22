"""
tests/test_ollama_fallback.py — Unit tests for the phi4-mini LLM fallback.

All Ollama calls are mocked — no real API calls are made.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.ollama_fallback import query
from classifier.schemas import EmailInput


def _email(subject: str = "Test", body: str = "Test body") -> EmailInput:
    return EmailInput(subject=subject, body=body, sender="test@example.com")


def _mock_ollama(response_text: str):
    """Return a context manager that mocks ollama.generate."""
    return patch(
        "classifier.ollama_fallback._call_ollama",
        return_value=response_text,
    )


# ── Valid JSON responses ───────────────────────────────────────────────────────

def test_valid_expense_response() -> None:
    raw = '{"label": "EXPENSE", "confidence_band": "high", "reason": "Invoice found"}'
    with _mock_ollama(raw):
        result = query(_email("Invoice", "INR 500"))
    assert result["label"] == "EXPENSE"
    assert result["confidence_band"] == "high"
    assert result["confidence_score"] == 0.9


def test_valid_not_expense_response() -> None:
    raw = '{"label": "NOT_EXPENSE", "confidence_band": "medium", "reason": "Social email"}'
    with _mock_ollama(raw):
        result = query(_email("Team lunch", "Free lunch"))
    assert result["label"] == "NOT_EXPENSE"
    assert result["confidence_band"] == "medium"


def test_valid_review_response() -> None:
    raw = '{"label": "REVIEW", "confidence_band": "low", "reason": "Uncertain content"}'
    with _mock_ollama(raw):
        result = query(_email("??", "ambiguous"))
    assert result["label"] == "REVIEW"
    assert result["confidence_band"] == "low"


# ── Invalid JSON handling ──────────────────────────────────────────────────────

def test_invalid_json_returns_review() -> None:
    """Both attempts return invalid JSON → must return REVIEW, never guess."""
    with _mock_ollama("This is not JSON at all, sorry."):
        result = query(_email("Vague", "body"))
    assert result["label"] == "REVIEW"
    assert result["confidence_band"] == "low"


def test_json_with_wrong_label_returns_review() -> None:
    """JSON with an unexpected label value should be treated as invalid."""
    raw = '{"label": "MAYBE", "confidence_band": "high", "reason": "?"}'
    with _mock_ollama(raw):
        result = query(_email("Subject", "body"))
    assert result["label"] == "REVIEW"


def test_ollama_exception_returns_review() -> None:
    """If ollama raises an exception on both attempts, return REVIEW."""
    with patch("classifier.ollama_fallback._call_ollama", side_effect=Exception("timeout")):
        result = query(_email("Subject", "body"))
    assert result["label"] == "REVIEW"


# ── Prompt version is always included ─────────────────────────────────────────

def test_prompt_version_in_result() -> None:
    raw = '{"label": "EXPENSE", "confidence_band": "high", "reason": "ok"}'
    with _mock_ollama(raw):
        result = query(_email())
    assert "prompt_version" in result
