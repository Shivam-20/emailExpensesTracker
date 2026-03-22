"""
tests/test_distilbert_model.py — Unit tests for classifier/distilbert_model.py.

Tests that need torch use pytest.importorskip so they are skipped gracefully
if torch is not installed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.schemas import EmailInput


def _make_email(subject="Order confirmation", body="₹999 charged") -> EmailInput:
    return EmailInput(subject=subject, body=body, sender="shop@example.com")


def _make_mock_model_and_tokenizer(label: str = "EXPENSE", prob: float = 0.92):
    """Return fake HuggingFace model and tokenizer using real torch tensors."""
    torch = pytest.importorskip("torch")

    tokenizer = MagicMock()
    tokenizer.return_value = {
        "input_ids":      torch.tensor([[1, 2, 3]]),
        "attention_mask": torch.tensor([[1, 1, 1]]),
    }

    model = MagicMock()
    model.config.id2label = {0: "EXPENSE", 1: "NOT_EXPENSE"}
    idx         = 0 if label == "EXPENSE" else 1
    other_prob  = 1.0 - prob
    logit_vals  = [prob * 10, other_prob * 10] if idx == 0 else [other_prob * 10, prob * 10]
    output      = MagicMock()
    output.logits = torch.tensor([logit_vals])
    model.return_value = output
    model.eval = MagicMock(return_value=None)
    return model, tokenizer


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDistilbertClassify:

    def test_classify_expense_high_confidence(self, monkeypatch):
        """Fine-tuned model loaded → high-confidence EXPENSE result."""
        pytest.importorskip("torch")
        from classifier import distilbert_model as dm

        model, tokenizer = _make_mock_model_and_tokenizer("EXPENSE", 0.93)
        monkeypatch.setattr(dm, "_model",     model)
        monkeypatch.setattr(dm, "_tokenizer", tokenizer)
        monkeypatch.setattr(dm, "_label_map", {0: "EXPENSE", 1: "NOT_EXPENSE"})
        monkeypatch.setattr(dm, "_load_model", lambda: None)

        result = dm.classify(_make_email())
        assert result["label"] == "EXPENSE"
        assert result["confidence_band"] in ("high", "medium")

    def test_classify_not_expense(self, monkeypatch):
        """NOT_EXPENSE label returned when model predicts NOT_EXPENSE."""
        pytest.importorskip("torch")
        from classifier import distilbert_model as dm

        model, tokenizer = _make_mock_model_and_tokenizer("NOT_EXPENSE", 0.88)
        monkeypatch.setattr(dm, "_model",     model)
        monkeypatch.setattr(dm, "_tokenizer", tokenizer)
        monkeypatch.setattr(dm, "_label_map", {0: "EXPENSE", 1: "NOT_EXPENSE"})
        monkeypatch.setattr(dm, "_load_model", lambda: None)

        result = dm.classify(_make_email(subject="Newsletter", body="Unsubscribe"))
        assert result["label"] == "NOT_EXPENSE"

    def test_classify_low_confidence_band(self, monkeypatch):
        """Low confidence score → confidence_band 'low'."""
        pytest.importorskip("torch")
        from classifier import distilbert_model as dm

        # prob=0.51 produces nearly-equal logits → softmax max ≈ 0.525 → "low" band
        model, tokenizer = _make_mock_model_and_tokenizer("EXPENSE", 0.51)
        monkeypatch.setattr(dm, "_model",     model)
        monkeypatch.setattr(dm, "_tokenizer", tokenizer)
        monkeypatch.setattr(dm, "_label_map", {0: "EXPENSE", 1: "NOT_EXPENSE"})
        monkeypatch.setattr(dm, "_load_model", lambda: None)

        result = dm.classify(_make_email())
        assert result["confidence_band"] == "low"

    def test_base_model_used_as_fallback_when_no_fine_tuned(self, tmp_path, monkeypatch):
        """If models/distilbert/ does not exist, classify() returns REVIEW."""
        from classifier import distilbert_model as dm

        monkeypatch.setattr(dm, "_HAS_TRANSFORMERS", True)
        monkeypatch.setattr(dm, "_model",     None)
        monkeypatch.setattr(dm, "_tokenizer", None)
        monkeypatch.setattr(dm, "_label_map", {})

        # _load_model raises FileNotFoundError → should return REVIEW
        def _raise():
            raise FileNotFoundError("Fine-tuned DistilBERT model not found")
        monkeypatch.setattr(dm, "_load_model", _raise)

        result = dm.classify(_make_email())
        assert result["label"] == "REVIEW"
        reason_lower = result["reason"].lower()
        assert "not trained" in reason_lower or "not found" in reason_lower or "model" in reason_lower

    def test_classify_returns_required_keys(self, monkeypatch):
        """classify() always returns all required dict keys."""
        pytest.importorskip("torch")
        from classifier import distilbert_model as dm

        model, tokenizer = _make_mock_model_and_tokenizer("EXPENSE", 0.9)
        monkeypatch.setattr(dm, "_model",     model)
        monkeypatch.setattr(dm, "_tokenizer", tokenizer)
        monkeypatch.setattr(dm, "_label_map", {0: "EXPENSE", 1: "NOT_EXPENSE"})
        monkeypatch.setattr(dm, "_load_model", lambda: None)

        result = dm.classify(_make_email())
        for key in ("label", "confidence_score", "confidence_band", "reason"):
            assert key in result, f"Missing key: {key}"

    def test_classify_no_transformers_returns_review(self, monkeypatch):
        """If transformers is not installed, classify() returns REVIEW gracefully."""
        from classifier import distilbert_model as dm
        monkeypatch.setattr(dm, "_HAS_TRANSFORMERS", False)

        result = dm.classify(_make_email())
        assert result["label"] == "REVIEW"
        assert result["confidence_band"] == "low"

    def test_classify_empty_body(self, monkeypatch):
        """classify() handles empty body without crashing."""
        pytest.importorskip("torch")
        from classifier import distilbert_model as dm

        model, tokenizer = _make_mock_model_and_tokenizer("NOT_EXPENSE", 0.75)
        monkeypatch.setattr(dm, "_model",     model)
        monkeypatch.setattr(dm, "_tokenizer", tokenizer)
        monkeypatch.setattr(dm, "_label_map", {0: "EXPENSE", 1: "NOT_EXPENSE"})
        monkeypatch.setattr(dm, "_load_model", lambda: None)

        result = dm.classify(EmailInput(subject="Hi", body="", sender="x@y.com"))
        assert result["label"] in ("EXPENSE", "NOT_EXPENSE", "REVIEW")
