"""
core/deduplicator.py — Identify duplicate expense emails.

Two expenses are duplicates if:
  - Same normalised sender domain
  - Same amount (within ±1%)
  - Date within a 3-day window
The later one is marked DUPLICATE; the earlier is kept ACTIVE.
"""

import re
from datetime import datetime, timedelta


def find_duplicates(expenses: list[dict]) -> list[dict]:
    """
    Mutate each expense dict's 'status' field:
      - Earlier occurrence → 'active'
      - Later  occurrence  → 'duplicate'

    Returns the same list (mutated in place) for convenience.
    """
    # Sort by date ascending so we always mark the *later* one
    sorted_expenses = sorted(expenses, key=lambda e: e.get("email_date", ""))

    for i, exp_a in enumerate(sorted_expenses):
        if exp_a.get("status") == "duplicate":
            continue
        domain_a = _sender_domain(exp_a.get("sender_email", ""))
        amount_a = exp_a.get("amount") or 0
        date_a   = _parse_date(exp_a.get("email_date", ""))

        for exp_b in sorted_expenses[i + 1:]:
            if exp_b.get("status") == "duplicate":
                continue
            domain_b = _sender_domain(exp_b.get("sender_email", ""))
            amount_b = exp_b.get("amount") or 0
            date_b   = _parse_date(exp_b.get("email_date", ""))

            if domain_a != domain_b:
                continue

            # Amount within ±1%
            if amount_a > 0 and abs(amount_a - amount_b) / amount_a > 0.01:
                continue

            # Date within 3 days
            if date_a and date_b and abs((date_b - date_a).days) > 3:
                continue

            exp_b["status"] = "duplicate"

    return sorted_expenses


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sender_domain(email: str) -> str:
    """Return lowercase domain from an email address, or the whole string."""
    m = re.search(r"@([\w.\-]+)", email)
    return m.group(1).lower() if m else email.lower()


def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
