"""
classifier/router.py — Pipeline orchestrator.

Runs stages in strict order per AGENTS.md:
  Stage 1 → rules.py        (always runs)
  Stage 2 → ml_model.py     (only if Stage 1 is uncertain)
  Stage 3 → pipeline (DistilBERT/phi4-mini) (only if Stage 2 is uncertain)
  Fallback → return REVIEW

Never skip Stage 1.
Never call Stage 3 unless Stage 1 and Stage 2 are both uncertain.
Stage 3 uses pipeline with configurable mode and models.
"""

import logging

from .config import (
    LLM_ACCEPT_BANDS,
    LLM_REVIEW_BAND,
    ML_HIGH_THRESHOLD,
    ML_LOW_THRESHOLD,
    RULE_HIGH_THRESHOLD,
    RULE_ZERO_THRESHOLD,
)
from .pipeline import Pipeline, PipelineMode, load_pipeline_config
from .rules import score_email
from .schemas import ClassificationResult, EmailInput
from .utils import band_from_score

logger = logging.getLogger(__name__)


def _classify_with_stage3(email: EmailInput) -> dict:
    """
    Use pipeline for Stage 3 classification.

    Loads pipeline config, creates Pipeline object with config's mode and active models,
    and uses pipeline.predict() for final classification.

    Returns a dict with keys: label, confidence_score, confidence_band, reason.

    Falls back to original DistilBERT/phi4-mini if pipeline config is empty or fails.
    """
    try:
        config = load_pipeline_config()
        if not config or not config.get("active_models"):
            raise ValueError("Empty pipeline config")

        mode_str = config.get("mode", "ensemble")
        mode = PipelineMode.ENSEMBLE if mode_str == "ensemble" else PipelineMode.CASCADE

        pipeline = Pipeline(
            models=config["active_models"],
            mode=mode,
            cascade_threshold=config.get("cascade_threshold", 0.80),
        )

        result = pipeline.predict(
            subject=email.subject,
            sender=email.sender,
            body=email.body,
        )

        confidence = result.get("confidence", 0.0)
        label = result.get("label", "REVIEW")

        band = band_from_score(confidence)

        return {
            "label": label,
            "confidence_score": confidence,
            "confidence_band": band,
            "reason": f"pipeline ({mode_str}) classification",
        }

    except Exception as exc:
        logger.warning("Pipeline classification failed: %s — falling back to DistilBERT", exc)
        return get_stage3_result(email)


def _review_result(reason: str) -> ClassificationResult:
    return ClassificationResult(
        label="REVIEW",
        confidence_score=0.0,
        confidence_band="low",
        stage_used="review",
        reason=reason,
        needs_review=True,
    )


def get_stage3_result(email: EmailInput) -> dict:
    """
    Route to the configured Stage 3 backend (DistilBERT or phi4-mini).

    Returns a dict with keys: label, confidence_score, confidence_band, reason.
    """
    # Re-read backend at call time so runtime changes in Settings tab take effect
    from .config import _load_stage3_backend
    backend = _load_stage3_backend()

    if backend == "distilbert":
        from .distilbert_model import classify as distilbert_classify
        return distilbert_classify(email)
    else:
        from .ollama_fallback import classify as ollama_classify
        return ollama_classify(email)


def classify(email: EmailInput) -> ClassificationResult:
    """
    Classify a single email through the staged hybrid pipeline.

    Returns a ClassificationResult with label EXPENSE, NOT_EXPENSE, or REVIEW.
    """
    # ── Stage 1: Rule engine ──────────────────────────────────────────────────
    rule_score = score_email(email.subject, email.body, email.sender)
    logger.debug("Rule score: %d for subject=%r", rule_score, email.subject)

    if rule_score >= RULE_HIGH_THRESHOLD:
        score = min(1.0, 0.7 + (rule_score - RULE_HIGH_THRESHOLD) * 0.05)
        return ClassificationResult(
            label="EXPENSE",
            confidence_score=score,
            confidence_band=band_from_score(score),
            stage_used="rules",
            reason=f"Rule score {rule_score} >= threshold {RULE_HIGH_THRESHOLD}",
            needs_review=False,
        )

    if rule_score == RULE_ZERO_THRESHOLD:
        return ClassificationResult(
            label="NOT_EXPENSE",
            confidence_score=0.95,
            confidence_band="high",
            stage_used="rules",
            reason="Rule score 0 — no expense signals found",
            needs_review=False,
        )

    # ── Stage 2: ML model ─────────────────────────────────────────────────────
    try:
        from .ml_model import predict as ml_predict
        ml_result = ml_predict(email)
        ml_prob    = ml_result["probability"]
        ml_label   = ml_result["label"]
        logger.debug("ML prob=%.3f label=%s", ml_prob, ml_label)

        if ml_prob >= ML_HIGH_THRESHOLD:
            return ClassificationResult(
                label=ml_label,
                confidence_score=ml_prob,
                confidence_band=band_from_score(ml_prob),
                stage_used="naive_bayes_tfidf",
                reason=f"ML probability {ml_prob:.2f} >= {ML_HIGH_THRESHOLD}",
                needs_review=False,
            )

        if ml_prob >= ML_LOW_THRESHOLD:
            return ClassificationResult(
                label=ml_label,
                confidence_score=ml_prob,
                confidence_band="medium",
                stage_used="naive_bayes_tfidf",
                reason=f"ML probability {ml_prob:.2f} (medium confidence)",
                needs_review=False,
            )

        logger.debug("ML low confidence (%.3f) — escalating to Stage 3", ml_prob)

    except Exception as exc:
        logger.warning("ML stage failed: %s — escalating to Stage 3", exc)

    # ── Stage 3: Pipeline classification ─────────────────────────────────────────
    try:
        stage3_result = _classify_with_stage3(email)
        band          = stage3_result.get("confidence_band", "low")
        s3_label      = stage3_result.get("label", "REVIEW")
        s3_score      = stage3_result.get("confidence_score", 0.0)
        stage_name    = "pipeline"
        logger.debug("Stage3[%s] band=%s label=%s", stage_name, band, s3_label)

        if band in LLM_ACCEPT_BANDS:
            return ClassificationResult(
                label=s3_label,
                confidence_score=s3_score,
                confidence_band=band,
                stage_used=stage_name,
                reason=stage3_result.get("reason", "pipeline classification"),
                needs_review=False,
            )

        if band == LLM_REVIEW_BAND:
            return _review_result(
                f"Stage 3 [{stage_name}] returned low confidence — sending for human review"
            )

    except Exception as exc:
        logger.warning("Stage 3 failed: %s — returning REVIEW", exc)

    # ── Fallback ──────────────────────────────────────────────────────────────
    return _review_result("All stages uncertain — defaulting to REVIEW")
