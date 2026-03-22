"""
classifier/rules.py — Stage 1: keyword scoring engine.

Scores an email on how likely it is an expense.
A score >= RULE_HIGH_THRESHOLD → EXPENSE.
A score == RULE_ZERO_THRESHOLD → NOT_EXPENSE.
Otherwise → uncertain (escalate to Stage 2).
"""

import logging
import re

from .preprocess import clean_text

logger = logging.getLogger(__name__)

# ── Weighted keyword list ─────────────────────────────────────────────────────
# (keyword/pattern, weight)
# Patterns beginning with 're:' are treated as regular expressions.
EXPENSE_KEYWORDS: list[tuple[str, int]] = [
    # Strong transactional signals (weight 3)
    ("invoice",          3),
    ("receipt",          3),
    ("payment confirmed", 3),
    ("order confirmed",  3),
    ("transaction",      3),
    ("debit",            3),
    ("charged",          3),
    ("re:amount due",    3),

    # Medium signals (weight 2)
    ("payment",          2),
    ("bill",             2),
    ("purchase",         2),
    ("booking confirmed", 2),
    ("subscription",     2),
    ("renewal",          2),
    ("auto-debit",       2),
    ("paid",             2),
    ("re:\\binr\\b",     2),   # regex: word boundary INR
    ("re:₹\\s*\\d",      2),   # regex: ₹ followed by digit
    ("re:rs\\.?\\s*\\d", 2),   # regex: Rs. followed by digit
    ("re:\\$\\s*\\d",    2),   # regex: $ followed by digit

    # Light signals (weight 1)
    ("order",            1),
    ("shipped",          1),
    ("delivery",         1),
    ("recharge",         1),
    ("top-up",           1),
    ("emi",              1),
    ("cashback",         1),
    ("refund",           1),
]

# ── Keywords that strongly indicate NOT an expense ────────────────────────────
NEGATIVE_KEYWORDS: list[tuple[str, int]] = [
    ("unsubscribe",          -3),
    ("newsletter",           -3),
    ("sale ends",            -2),
    ("last chance",          -2),
    ("limited time offer",   -2),
    ("team lunch",           -3),
    ("social",               -1),
    ("invite",               -1),
    ("re:save \\d+%",        -2),  # regex: "save 20%"
]


def _match_keyword(keyword: str, text: str) -> bool:
    """Match a plain keyword or regex (prefixed with 're:') against text."""
    if keyword.startswith("re:"):
        return bool(re.search(keyword[3:], text, re.IGNORECASE))
    return keyword in text


def score_email(subject: str, body: str, sender: str) -> int:
    """
    Return an integer expense score for the email.

    Positive contributions from EXPENSE_KEYWORDS.
    Negative contributions from NEGATIVE_KEYWORDS.
    Score is clamped to [0, 10].
    """
    text = clean_text(f"{subject} {sender} {body[:3000]}")
    score = 0

    for keyword, weight in EXPENSE_KEYWORDS:
        if _match_keyword(keyword, text):
            score += weight
            logger.debug("Rule hit (+%d): %s", weight, keyword)

    for keyword, weight in NEGATIVE_KEYWORDS:
        if _match_keyword(keyword, text):
            score += weight   # weight is already negative
            logger.debug("Rule hit (%d): %s", weight, keyword)

    return max(0, min(score, 10))
