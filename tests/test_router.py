"""
tests/test_router.py — Integration tests for the pipeline router.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.router import classify, get_stage3_result
from classifier.schemas import ClassificationResult, EmailInput


def _email(subject: str, body: str, sender: str = "test@example.com") -> EmailInput:
    return EmailInput(subject=subject, body=body, sender=sender)


# ── Stage 1 tests ─────────────────────────────────────────────────────────────

def test_clear_invoice_classified_as_expense_by_rules() -> None:
    """A high-scoring invoice email should be classified by Stage 1 rules."""
    result = classify(_email(
        subject="Invoice #4521 attached",
        body="Please find the invoice for INR 4500. Payment confirmed. Transaction complete.",
        sender="billing@vendor.com",
    ))
    assert result.label == "EXPENSE"
    assert result.stage_used == "rules"
    assert result.needs_review is False


def test_social_lunch_classified_as_not_expense_by_rules() -> None:
    """A zero-score email should be classified as NOT_EXPENSE by Stage 1."""
    result = classify(_email(
        subject="Team social lunch",
        body="Hey everyone, join us for a fun team social lunch. Completely free!",
        sender="hr@company.com",
    ))
    assert result.label == "NOT_EXPENSE"
    assert result.stage_used == "rules"


# ── Stage 2 escalation ────────────────────────────────────────────────────────

def test_vague_email_escalates_to_ml() -> None:
    """An email with 1–5 rule score should attempt Stage 2 (ML)."""
    mock_ml = {"label": "EXPENSE", "probability": 0.9}
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml):
        result = classify(_email("Approval request", "Please review the attached doc"))
    assert result.stage_used == "naive_bayes_tfidf"
    assert result.label == "EXPENSE"


def test_ml_low_confidence_escalates_to_llm() -> None:
    """ML probability < 0.55 should escalate to Stage 3 (LLM / phi4-mini)."""
    mock_ml  = {"label": "EXPENSE", "probability": 0.45}
    mock_llm = {
        "label": "EXPENSE", "confidence_band": "high",
        "confidence_score": 0.9, "reason": "LLM says expense",
    }
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml), \
         patch("classifier.ollama_fallback.classify", return_value=mock_llm), \
         patch("classifier.config._load_stage3_backend", return_value="phi4-mini"):
        result = classify(_email("Vague request", "Can you look at this?"))
    assert result.stage_used == "phi4-mini"


# ── REVIEW fallback ───────────────────────────────────────────────────────────

def test_all_stages_uncertain_returns_review() -> None:
    """When all stages fail/are uncertain, router must return REVIEW."""
    mock_ml  = {"label": "EXPENSE", "probability": 0.45}
    mock_llm = {
        "label": "REVIEW", "confidence_band": "low",
        "confidence_score": 0.0, "reason": "Uncertain",
    }
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml), \
         patch("classifier.ollama_fallback.classify", return_value=mock_llm), \
         patch("classifier.config._load_stage3_backend", return_value="phi4-mini"):
        result = classify(_email("??", "ambiguous content"))
    assert result.label == "REVIEW"
    assert result.needs_review is True


def test_result_schema_always_complete() -> None:
    """ClassificationResult must always have all required fields."""
    result = classify(_email("Invoice paid", "₹500 receipt. Transaction complete."))
    assert isinstance(result, ClassificationResult)
    assert result.label in {"EXPENSE", "NOT_EXPENSE", "REVIEW"}
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.confidence_band in {"high", "medium", "low"}
    assert result.stage_used in {"rules", "naive_bayes_tfidf", "phi4-mini", "distilbert", "review"}
    assert isinstance(result.needs_review, bool)
    assert isinstance(result.reason, str)


# ── Stage 3 backend routing tests ─────────────────────────────────────────────

def test_stage3_routes_to_distilbert_when_configured(monkeypatch) -> None:
    """get_stage3_result() calls distilbert_model.classify when backend=distilbert."""
    mock_result = {
        "label": "EXPENSE", "confidence_score": 0.88,
        "confidence_band": "high", "reason": "distilbert says so",
    }
    with patch("classifier.distilbert_model.classify", return_value=mock_result) as mock_db, \
         patch("classifier.config._load_stage3_backend", return_value="distilbert"):
        result = get_stage3_result(_email("Order", "₹500"))
    mock_db.assert_called_once()
    assert result["label"] == "EXPENSE"


def test_stage3_routes_to_phi4mini_when_configured(monkeypatch) -> None:
    """get_stage3_result() calls ollama_fallback.classify when backend=phi4-mini."""
    mock_result = {
        "label": "EXPENSE", "confidence_score": 0.85,
        "confidence_band": "high", "reason": "ollama says so",
    }
    with patch("classifier.ollama_fallback.classify", return_value=mock_result) as mock_ol, \
         patch("classifier.config._load_stage3_backend", return_value="phi4-mini"):
        result = get_stage3_result(_email("Order", "₹500"))
    mock_ol.assert_called_once()
    assert result["label"] == "EXPENSE"


def test_distilbert_stage3_result_appears_in_full_pipeline(monkeypatch) -> None:
    """Full pipeline with distilbert backend: stage_used should be 'distilbert'."""
    mock_ml  = {"label": "EXPENSE", "probability": 0.45}
    mock_db  = {
        "label": "EXPENSE", "confidence_score": 0.9,
        "confidence_band": "high", "reason": "distilbert high",
    }
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml), \
         patch("classifier.distilbert_model.classify", return_value=mock_db), \
         patch("classifier.config._load_stage3_backend", return_value="distilbert"):
        result = classify(_email("Vague", "content"))
    assert result.stage_used == "distilbert"
    assert result.label == "EXPENSE"


def test_phi4mini_stage3_result_appears_in_full_pipeline(monkeypatch) -> None:
    """Full pipeline with phi4-mini backend: stage_used should be 'phi4-mini'."""
    mock_ml  = {"label": "EXPENSE", "probability": 0.45}
    mock_llm = {
        "label": "NOT_EXPENSE", "confidence_score": 0.82,
        "confidence_band": "high", "reason": "phi4 high",
    }
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml), \
         patch("classifier.ollama_fallback.classify", return_value=mock_llm), \
         patch("classifier.config._load_stage3_backend", return_value="phi4-mini"):
        result = classify(_email("Vague", "content"))
    assert result.stage_used == "phi4-mini"
    assert result.label == "NOT_EXPENSE"


def test_stage3_failure_returns_review() -> None:
    """If Stage 3 raises, router should return REVIEW instead of crashing."""
    mock_ml = {"label": "EXPENSE", "probability": 0.45}
    with patch("classifier.router.score_email", return_value=3), \
         patch("classifier.ml_model.predict", return_value=mock_ml), \
         patch("classifier.router.get_stage3_result", side_effect=RuntimeError("backend hung")), \
         patch("classifier.config._load_stage3_backend", return_value="distilbert"):
        result = classify(_email("Vague", "content"))
    assert result.label == "REVIEW"
    assert result.needs_review is True
