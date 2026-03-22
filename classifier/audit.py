"""
classifier/audit.py — Append every classification to the CSV audit log.

Log fields (per AGENTS.md):
    timestamp, email_id, label, confidence_score, stage_used,
    rule_score, ml_score, llm_confidence_band, stage3_backend, needs_review, reason

Rules:
- Never log email body content.
- Use this module for all audit logging — never write to the CSV directly.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

from .config import AUDIT_LOG
from .schemas import ClassificationResult

logger = logging.getLogger(__name__)

_FIELDS = [
    "timestamp",
    "email_id",
    "label",
    "confidence_score",
    "stage_used",
    "rule_score",
    "ml_score",
    "llm_confidence_band",
    "stage3_backend",
    "needs_review",
    "reason",
]


def _ensure_header(log_path: Path) -> None:
    """Write CSV header if the file is new or empty."""
    if not log_path.exists() or log_path.stat().st_size == 0:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=_FIELDS).writeheader()


def log_classification(
    result: ClassificationResult,
    email_id: str = "",
    rule_score: int = 0,
    ml_score: float = 0.0,
    llm_confidence_band: str = "",
    stage3_backend: str = "",
) -> None:
    """
    Append one row to the audit CSV.

    Parameters
    ----------
    result              ClassificationResult from router.classify()
    email_id            Gmail message ID (or empty string)
    rule_score          Raw integer score from Stage 1 rules
    ml_score            ML probability from Stage 2 (0–1)
    llm_confidence_band Confidence band string from Stage 3
    stage3_backend      Backend used for Stage 3: "distilbert" | "phi4-mini" | ""
    """
    _ensure_header(AUDIT_LOG)

    # Auto-detect stage3_backend from result if not explicitly provided
    if not stage3_backend and result.stage_used in ("distilbert", "phi4-mini"):
        stage3_backend = result.stage_used

    row = {
        "timestamp":           datetime.utcnow().isoformat(),
        "email_id":            email_id,
        "label":               result.label,
        "confidence_score":    round(result.confidence_score, 4),
        "stage_used":          result.stage_used,
        "rule_score":          rule_score,
        "ml_score":            round(ml_score, 4),
        "llm_confidence_band": llm_confidence_band,
        "stage3_backend":      stage3_backend,
        "needs_review":        int(result.needs_review),
        "reason":              result.reason,
    }
    try:
        with AUDIT_LOG.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=_FIELDS).writerow(row)
    except OSError as exc:
        logger.error("Failed to write audit log: %s", exc)
