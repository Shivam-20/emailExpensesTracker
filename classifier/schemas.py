"""
classifier/schemas.py — Input and output dataclasses for the classifier pipeline.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class EmailInput:
    """Represents a single email to be classified."""
    subject: str
    body: str
    sender: str
    sender_email: str = ""
    attachments: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """
    Unified output schema for all classifier stages.

    Every function that classifies must return an instance matching this schema.
    """
    label: Literal["EXPENSE", "NOT_EXPENSE", "REVIEW"]
    confidence_score: float                         # 0.0 to 1.0
    confidence_band: Literal["high", "medium", "low"]
    stage_used: Literal["rules", "naive_bayes_tfidf", "distilbert", "phi4-mini", "review"]
    reason: str
    needs_review: bool

    def to_dict(self) -> dict:
        return {
            "label":            self.label,
            "confidence_score": self.confidence_score,
            "confidence_band":  self.confidence_band,
            "stage_used":       self.stage_used,
            "reason":           self.reason,
            "needs_review":     self.needs_review,
        }
