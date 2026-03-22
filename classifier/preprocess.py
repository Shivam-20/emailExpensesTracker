"""
classifier/preprocess.py — Text cleaning and feature extraction for the classifier.
"""

import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# ── Patterns used in feature extraction ──────────────────────────────────────
_CURRENCY_RE    = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)", re.IGNORECASE)
_AMOUNT_RE      = re.compile(
    r"(?:total|amount|paid|charged|price|cost|bill|due)\s*[:\-]?\s*"
    r"(?:INR|Rs\.?|₹|\$|USD|EUR|£|GBP)?\s*[\d,]+(?:\.\d{1,2})?",
    re.IGNORECASE,
)
_HTML_TAG_RE    = re.compile(r"<[^>]+>")
_WHITESPACE_RE  = re.compile(r"\s+")


class _HTMLStripper(HTMLParser):
    """Minimal HTML stripper that avoids external dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(text: str) -> str:
    """Remove HTML tags and return plain text."""
    stripper = _HTMLStripper()
    try:
        stripper.feed(text)
        return stripper.get_text()
    except Exception:
        return _HTML_TAG_RE.sub(" ", text)


def clean_text(text: str) -> str:
    """
    Lowercase, strip HTML, collapse whitespace.

    Used to normalise text before feature extraction and scoring.
    """
    text = strip_html(text)
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def has_currency_symbol(text: str) -> bool:
    """Return True if any known currency symbol or word is present."""
    return bool(_CURRENCY_RE.search(text))


def has_amount_keyword(text: str) -> bool:
    """Return True if a labelled amount pattern (total/paid/charged…) is found."""
    return bool(_AMOUNT_RE.search(text))


def has_attachment(attachments: list[str]) -> bool:
    """Return True if the email has at least one attachment."""
    return len(attachments) > 0


def extract_features(
    subject: str,
    body: str,
    sender: str,
    attachments: list[str],
) -> dict:
    """
    Return a feature dict for the ML model and rule engine.

    Keys:
        combined_text   — cleaned subject + sender + body for TF-IDF
        has_currency    — bool
        has_amount_kw   — bool
        has_attachment  — bool
        subject_clean   — cleaned subject
    """
    combined = clean_text(f"{subject} {sender} {body[:3000]}")
    return {
        "combined_text":  combined,
        "has_currency":   has_currency_symbol(combined),
        "has_amount_kw":  has_amount_keyword(combined),
        "has_attachment": has_attachment(attachments),
        "subject_clean":  clean_text(subject),
    }
