"""
tests/test_ml_model.py — Unit tests for the TF-IDF + Naive Bayes model.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Skip all tests if scikit-learn is not installed
sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")
pd      = pytest.importorskip("pandas",  reason="pandas not installed")
joblib  = pytest.importorskip("joblib",  reason="joblib not installed")


def _temp_csv(rows: list[dict]) -> Path:
    import pandas as _pd
    p = Path(tempfile.mktemp(suffix=".csv"))
    _pd.DataFrame(rows).to_csv(p, index=False)
    return p


@pytest.fixture()
def trained_model(tmp_path: Path):
    """Train a minimal model in a temp directory and return (model_path, vec_path)."""
    from classifier.ml_model import train

    training_rows = [
        {"subject": "Invoice attached",       "body": "INR 4500 payment",         "sender": "billing@x.com",    "label": "EXPENSE"},
        {"subject": "Receipt for order",      "body": "₹1200 charged to card",    "sender": "shop@y.com",       "label": "EXPENSE"},
        {"subject": "Payment confirmed",      "body": "Your payment was received", "sender": "bank@z.com",       "label": "EXPENSE"},
        {"subject": "Team lunch invite",      "body": "No cost, HR sponsored",     "sender": "hr@co.com",        "label": "NOT_EXPENSE"},
        {"subject": "Newsletter this week",   "body": "Unsubscribe below",         "sender": "news@blog.com",    "label": "NOT_EXPENSE"},
        {"subject": "Meeting rescheduled",    "body": "Meeting at 3 PM",           "sender": "cal@co.com",       "label": "NOT_EXPENSE"},
    ]
    import pandas as _pd
    csv_path = tmp_path / "train.csv"
    _pd.DataFrame(training_rows).to_csv(csv_path, index=False)

    model_path = tmp_path / "model.joblib"
    vec_path   = tmp_path / "vec.joblib"
    train(csv_path, model_path, vec_path, verbose=False)
    return model_path, vec_path


def test_model_file_created(trained_model, tmp_path: Path) -> None:
    model_path, _ = trained_model
    assert model_path.exists(), "Model file should be created after training"


def test_predict_expense(trained_model, monkeypatch) -> None:
    from classifier import ml_model, schemas

    model_path, _ = trained_model
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    email = schemas.EmailInput(
        subject="Invoice attached",
        body="INR 4500 payment received.",
        sender="billing@vendor.com",
    )
    result = ml_model.predict(email)
    assert result["label"] in {"EXPENSE", "NOT_EXPENSE"}
    assert 0.0 <= result["probability"] <= 1.0


def test_predict_not_expense(trained_model, monkeypatch) -> None:
    from classifier import ml_model, schemas

    model_path, _ = trained_model
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    email = schemas.EmailInput(
        subject="Team lunch this Friday",
        body="Everyone's invited! HR sponsored social lunch.",
        sender="hr@company.com",
    )
    result = ml_model.predict(email)
    assert result["label"] in {"EXPENSE", "NOT_EXPENSE"}
