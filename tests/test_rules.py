"""
tests/test_rules.py — Unit tests for the rule scoring engine.
"""

import sys
from pathlib import Path

# Allow imports from gmail_expense_tracker root
sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.rules import score_email


def test_clear_invoice_email_scores_high() -> None:
    """A clear invoice email should score >= RULE_HIGH_THRESHOLD (6)."""
    score = score_email(
        subject="Invoice #4521 attached",
        body="Please find attached invoice for INR 4500 for services rendered.",
        sender="billing@vendor.com",
    )
    assert score >= 6, f"Expected score >= 6, got {score}"


def test_social_lunch_scores_zero() -> None:
    """A social team lunch invite should score 0 — no expense signals."""
    score = score_email(
        subject="Team lunch this Friday!",
        body="Hey everyone, join us for a team social lunch. Sponsored by HR, no cost!",
        sender="hr@company.com",
    )
    assert score == 0, f"Expected score 0, got {score}"


def test_payment_confirmation_scores_high() -> None:
    score = score_email(
        subject="Payment confirmed",
        body="Your payment of ₹1200 has been received. Transaction ID: TXN123.",
        sender="noreply@bank.com",
    )
    assert score >= 6


def test_subscription_renewal_scores_high() -> None:
    score = score_email(
        subject="Netflix subscription renewal",
        body="Your monthly subscription has been renewed. Amount charged: ₹499.",
        sender="no-reply@netflix.com",
    )
    assert score >= 6


def test_newsletter_scores_low() -> None:
    score = score_email(
        subject="Top stories this week — your newsletter",
        body="Unsubscribe | This week's top tech headlines. Click to read more.",
        sender="newsletter@techblog.com",
    )
    assert score <= 2, f"Expected score <= 2, got {score}"


def test_score_is_clamped_between_0_and_10() -> None:
    """Score must never go below 0 or above 10."""
    score = score_email(
        subject="invoice receipt payment transaction charged debit",
        body="INR ₹ Rs paid total amount bill purchase booking subscription",
        sender="billing@bank.com",
    )
    assert 0 <= score <= 10
