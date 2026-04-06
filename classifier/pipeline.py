"""
classifier/pipeline.py — Ensemble/Cascade prediction pipeline.

Public API:
    PipelineMode: Enum with ENSEMBLE and CASCADE modes
    Pipeline: Main class for multi-model prediction
    load_pipeline_config(): Load config from data/pipeline_config.json
    save_pipeline_config(config): Save config to file
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """Pipeline operating mode."""
    ENSEMBLE = "ensemble"
    CASCADE = "cascade"


# ── Config paths ───────────────────────────────────────────────────────────────
_PIPELINE_CONFIG_PATH = Path(__file__).parent.parent / "data" / "pipeline_config.json"

# ── Default configuration ───────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "mode": "ensemble",
    "active_models": ["minilm-l6-v2", "tfidf-nb"],
    "cascade_threshold": 0.80,
}


def load_pipeline_config() -> dict[str, Any]:
    """Load pipeline configuration from data/pipeline_config.json."""
    try:
        if _PIPELINE_CONFIG_PATH.exists():
            config = json.loads(_PIPELINE_CONFIG_PATH.read_text())
            logger.info("Loaded pipeline config: %s", config)
            return config
    except Exception as e:
        logger.warning("Failed to load pipeline config: %s", e)
    return DEFAULT_CONFIG.copy()


def save_pipeline_config(config: dict[str, Any]) -> None:
    """Save pipeline configuration to data/pipeline_config.json."""
    _PIPELINE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PIPELINE_CONFIG_PATH.write_text(json.dumps(config, indent=2))
    logger.info("Saved pipeline config: %s", config)


# ── Model name mapping ───────────────────────────────────────────────────────
_MODEL_MAPPINGS: dict[str, str] = {
    "minilm-l6-v2": "minilm",
    "tfidf-nb": "tfidf-nb",
}


def _predict_with_model(model_name: str, subject: str, sender: str, body: str) -> dict[str, Any]:
    """
    Get prediction from a single model.

    Args:
        model_name: Model identifier (e.g., "minilm-l6-v2", "tfidf-nb")
        subject: Email subject
        sender: Email sender
        body: Email body

    Returns:
        dict with keys: label, confidence, model_name
    """
    mapped_name = _MODEL_MAPPINGS.get(model_name, model_name)

    if mapped_name == "tfidf-nb":
        return _predict_tfidf_nb(subject, sender, body)
    elif mapped_name in ("minilm", "tinybert", "albert", "mobilebert", "distilbert"):
        return _predict_lightweight(mapped_name, subject, sender, body)
    else:
        raise ValueError(f"Unknown model: {model_name}")


def _predict_tfidf_nb(subject: str, sender: str, body: str) -> dict[str, Any]:
    """Get prediction from TF-IDF + Naive Bayes model."""
    from .schemas import EmailInput

    result = ml_model.predict(EmailInput(subject=subject, sender=sender, body=body))
    return {
        "label": result["label"],
        "confidence": result["probability"],
        "model_name": "tfidf-nb",
    }


def _predict_lightweight(
    model_type: str, subject: str, sender: str, body: str
) -> dict[str, Any]:
    """Get prediction from lightweight transformer model."""
    result = lightweight_models.predict(model_type, subject, sender, body)
    return {
        "label": result["label"],
        "confidence": result["confidence"],
        "model_name": model_type,
    }


# ── Lazy imports for module-level access ──────────────────────────────────────
ml_model: Optional[Any] = None
lightweight_models: Optional[Any] = None


def _lazy_imports() -> None:
    global ml_model, lightweight_models
    if ml_model is None:
        from . import ml_model
    if lightweight_models is None:
        from . import lightweight_models


# ── Pipeline class ───────────────────────────────────────────────────────────


class Pipeline:
    """
    Multi-model prediction pipeline with ensemble and cascade modes.

    Ensemble: All models vote, majority wins
    Cascade: Use first model with confidence >= threshold, fallback to next
    """

    def __init__(
        self,
        models: list[str],
        mode: PipelineMode,
        cascade_threshold: Optional[float] = None,
    ) -> None:
        """
        Initialize pipeline with models and mode.

        Args:
            models: List of model identifiers
            mode: PipelineMode.ENSEMBLE or PipelineMode.CASCADE
            cascade_threshold: Threshold for cascade mode (default: 0.80)
        """
        if not models:
            raise ValueError("models list cannot be empty")

        valid_models = set(_MODEL_MAPPINGS.keys())
        unknown = set(models) - valid_models
        if unknown:
            raise ValueError(f"Unknown model(s): {unknown}. Valid models: {valid_models}")

        _lazy_imports()
        self.models = models
        self.mode = mode
        self.cascade_threshold = cascade_threshold if cascade_threshold is not None else 0.80
        logger.info("Pipeline initialized: mode=%s, models=%s, threshold=%.2f", mode.value, models, self.cascade_threshold)

    def predict(
        self, subject: str, sender: str, body: str
    ) -> dict[str, Any]:
        """
        Get ensemble or cascade prediction.

        Returns:
            dict with:
                - label: "EXPENSE" or "NOT_EXPENSE"
                - confidence: float (0-1)
                - votes: dict of model -> label (ensemble mode)
                - used_model: str (cascade mode)
        """
        if self.mode == PipelineMode.ENSEMBLE:
            return self._ensemble_predict(subject, sender, body)
        else:
            return self._cascade_predict(subject, sender, body)

    def _ensemble_predict(
        self, subject: str, sender: str, body: str
    ) -> dict[str, Any]:
        """Ensemble voting: all models vote, majority wins."""
        votes: dict[str, str] = {}
        total_confidence = 0.0

        for model_name in self.models:
            result = _predict_with_model(model_name, subject, sender, body)
            votes[model_name] = result["label"]
            total_confidence += result["confidence"]

        expense_votes = sum(1 for label in votes.values() if label == "EXPENSE")
        not_expense_votes = sum(1 for label in votes.values() if label == "NOT_EXPENSE")

        if expense_votes > not_expense_votes:
            label = "EXPENSE"
        elif not_expense_votes > expense_votes:
            label = "NOT_EXPENSE"
        else:
            label = "EXPENSE"

        avg_confidence = total_confidence / len(self.models) if self.models else 0.0

        return {
            "label": label,
            "confidence": avg_confidence,
            "votes": votes,
        }

    def _cascade_predict(
        self, subject: str, sender: str, body: str
    ) -> dict[str, Any]:
        """Cascade fallback: use first model with confidence >= threshold."""
        for model_name in self.models:
            result = _predict_with_model(model_name, subject, sender, body)
            if result["confidence"] >= self.cascade_threshold:
                logger.debug("Model %s passed threshold: %.2f", model_name, result["confidence"])
                return {
                    "label": result["label"],
                    "confidence": result["confidence"],
                    "used_model": model_name,
                }

        last_result = result
        logger.debug("No model passed threshold, using last: %s", last_result["model_name"])
        return {
            "label": last_result["label"],
            "confidence": last_result["confidence"],
            "used_model": last_result["model_name"],
        }
