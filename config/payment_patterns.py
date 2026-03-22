"""config/payment_patterns.py — Regex patterns for payment method detection."""

import re
from typing import Optional

# Ordered list of (method_name, [pattern_strings])
PAYMENT_PATTERNS: dict[str, list[str]] = {
    "UPI": [
        r"UPI\s*[Rr]ef(?:erence)?",
        r"UPI\s*[Ii][Dd]",
        r"@ok(?:axis|sbi|icici|hdfc|ybl|upi)",
        r"paid\s+via\s+upi",
        r"\bUPI\b",
        r"upi\s*transaction",
        r"gpay|google\s*pay(?!\s*later)",
        r"phonepe",
        r"bhim",
    ],
    "Credit Card": [
        r"credit\s*card",
        r"cc\s*ending",
        r"card\s+(?:no\.?|number)?\s*[Xx*•]{2,}\s*(\d{4})",
        r"charged\s+to\s+(?:your\s+)?(?:visa|mastercard|amex|rupay|diners)",
        r"(?:visa|mastercard|amex|rupay)\s+credit",
    ],
    "Debit Card": [
        r"debit\s*card",
        r"dc\s*ending\s*(?:in|with)?\s*[Xx*•]{2,}\s*(\d{4})",
        r"(?:visa|mastercard|rupay)\s+debit",
    ],
    "Net Banking": [
        r"net\s*banking",
        r"netbanking",
        r"\bNEFT\b",
        r"\bIMPS\b",
        r"\bRTGS\b",
        r"internet\s*banking",
    ],
    "Wallet": [
        r"paytm\s*wallet",
        r"amazon\s*pay",
        r"mobikwik",
        r"freecharge",
        r"\bwallet\b",
        r"airtel\s*money",
    ],
    "COD": [
        r"cash\s+on\s+delivery",
        r"\bCOD\b",
        r"pay\s+on\s+delivery",
    ],
}

# Compiled patterns cache
_compiled: dict[str, list[re.Pattern]] = {}

def _get_compiled() -> dict[str, list[re.Pattern]]:
    global _compiled
    if not _compiled:
        for method, patterns in PAYMENT_PATTERNS.items():
            _compiled[method] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return _compiled


def detect_payment_method(text: str) -> tuple[str, Optional[str]]:
    """
    Scan *text* for payment method patterns.
    Returns (method_name, last_4_digits_or_None).
    Defaults to ('Unknown', None) if nothing matches.
    """
    compiled = _get_compiled()
    for method, patterns in compiled.items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                last4: Optional[str] = None
                # Try to extract last 4 digits from card patterns
                if method in ("Credit Card", "Debit Card") and m.lastindex:
                    try:
                        last4 = m.group(1)
                    except IndexError:
                        pass
                return method, last4
    return "Unknown", None
