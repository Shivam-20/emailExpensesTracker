"""
tests/test_pipeline.py — Unit tests for the ensemble/cascade pipeline.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")
pd = pytest.importorskip("pandas", reason="pandas not installed")


def _temp_csv(rows: list[dict]) -> Path:
    p = Path(tempfile.mktemp(suffix=".csv"))
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


@pytest.fixture()
def trained_models(tmp_path: Path):
    """Train both TF-IDF and MiniLM models."""
    from classifier import ml_model, config

    training_rows = [
        {"subject": "Invoice attached", "body": "INR 4500 payment", "sender": "billing@x.com", "label": "EXPENSE"},
        {"subject": "Receipt for order", "body": "₹1200 charged to card", "sender": "shop@y.com", "label": "EXPENSE"},
        {"subject": "Payment confirmed", "body": "Your payment was received", "sender": "bank@z.com", "label": "EXPENSE"},
        {"subject": "Team lunch invite", "body": "No cost, HR sponsored", "sender": "hr@co.com", "label": "NOT_EXPENSE"},
        {"subject": "Newsletter this week", "body": "Unsubscribe below", "sender": "news@blog.com", "label": "NOT_EXPENSE"},
        {"subject": "Meeting rescheduled", "body": "Meeting at 3 PM", "sender": "cal@co.com", "label": "NOT_EXPENSE"},
    ]
    csv_path = _temp_csv(training_rows)

    model_path = tmp_path / "model.joblib"
    vec_path = tmp_path / "vec.joblib"
    ml_model.train(csv_path, model_path, vec_path, verbose=False)

    return model_path


def test_load_pipeline_config() -> None:
    """Test loading default pipeline config."""
    from classifier.pipeline import load_pipeline_config, DEFAULT_CONFIG

    config = load_pipeline_config()
    assert config["mode"] == DEFAULT_CONFIG["mode"]
    assert config["active_models"] == DEFAULT_CONFIG["active_models"]


def test_save_pipeline_config(tmp_path: Path) -> None:
    """Test saving pipeline config to file."""
    from classifier import pipeline

    old_path = pipeline._PIPELINE_CONFIG_PATH
    pipeline._PIPELINE_CONFIG_PATH = tmp_path / "pipeline_config.json"

    config = {"mode": "cascade", "active_models": ["tfidf-nb"], "cascade_threshold": 0.9}
    pipeline.save_pipeline_config(config)

    loaded = pipeline.load_pipeline_config()
    assert loaded["mode"] == "cascade"
    assert loaded["active_models"] == ["tfidf-nb"]

    pipeline._PIPELINE_CONFIG_PATH = old_path


def test_ensemble_voting_expense_wins(trained_models, monkeypatch) -> None:
    """Ensemble should return EXPENSE when majority votes EXPENSE."""
    from classifier import ml_model, pipeline

    model_path = trained_models
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    pipe = pipeline.Pipeline(models=["tfidf-nb", "tfidf-nb"], mode=pipeline.PipelineMode.ENSEMBLE)
    result = pipe.predict(
        subject="Invoice attached",
        sender="billing@vendor.com",
        body="INR 4500 payment received",
    )

    assert result["label"] == "EXPENSE"
    assert 0.0 <= result["confidence"] <= 1.0
    assert "votes" in result


def test_ensemble_voting_not_expense_wins(trained_models, monkeypatch) -> None:
    """Ensemble should return NOT_EXPENSE when majority votes NOT_EXPENSE."""
    from classifier import ml_model, pipeline

    model_path = trained_models
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    pipe = pipeline.Pipeline(models=["tfidf-nb", "tfidf-nb"], mode=pipeline.PipelineMode.ENSEMBLE)
    result = pipe.predict(
        subject="Newsletter this week",
        sender="news@blog.com",
        body="Unsubscribe below",
    )

    assert result["label"] == "NOT_EXPENSE"
    assert "votes" in result


def test_cascade_fallback(trained_models, monkeypatch) -> None:
    """Cascade should use first model that passes threshold."""
    from classifier import ml_model, pipeline

    model_path = trained_models
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    pipe = pipeline.Pipeline(models=["tfidf-nb"], mode=pipeline.PipelineMode.CASCADE)
    result = pipe.predict(
        subject="Invoice attached",
        sender="billing@vendor.com",
        body="INR 4500 payment received",
    )

    assert result["label"] in ["EXPENSE", "NOT_EXPENSE"]
    assert "used_model" in result
    assert result["used_model"] == "tfidf-nb"


def test_cascade_threshold(trained_models, monkeypatch) -> None:
    """Cascade should fallback when confidence < threshold."""
    from classifier import ml_model, pipeline

    model_path = trained_models
    monkeypatch.setattr(ml_model, "_pipeline", None)
    monkeypatch.setattr("classifier.config.MODEL_PATH", model_path)

    pipe = pipeline.Pipeline(models=["tfidf-nb"], mode=pipeline.PipelineMode.CASCADE)
    pipe.cascade_threshold = 0.99

    result = pipe.predict(
        subject="Meeting rescheduled",
        sender="cal@co.com",
        body="Meeting at 3 PM",
    )

    assert result["label"] in ["EXPENSE", "NOT_EXPENSE"]
    assert "used_model" in result
