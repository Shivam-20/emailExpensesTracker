"""
classifier/utils.py — Shared helpers used across classifier stages.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


def sha256_hash(subject: str, body: str, sender: str, attachments: list[str]) -> str:
    """Return a SHA-256 hex digest of the email fields used as cache key."""
    raw = f"{subject}|{body}|{sender}|{','.join(sorted(attachments))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def band_from_score(score: float) -> str:
    """
    Map a 0–1 probability score to a human-readable confidence band.

    Returns 'high', 'medium', or 'low'.
    """
    if score >= 0.85:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def safe_float(value: object, default: float = 0.0) -> float:
    """Convert value to float safely, returning default on failure."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
