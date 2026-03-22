"""
core/expense_parser.py — Parse Gmail messages into expense dicts.

Extracts: amount, currency, payment method, confidence, category.
"""

import base64
import json
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Amount extraction patterns ────────────────────────────────────────────────
# Pattern group 1 → HIGH confidence (keyword + optional currency + number)
_HIGH_PATTERNS = [
    r"(?:total|amount|paid|charged|price|cost|bill|due|subtotal|grand total)"
    r"\s*[:\-]?\s*(?:INR|Rs\.?|₹|\$|USD|EUR|£|GBP)?\s*([\d,]+(?:\.\d{1,2})?)",
]
# Pattern group 2 → MEDIUM confidence (currency symbol + number)
_MEDIUM_PATTERNS = [
    r"(?:INR|Rs\.?|₹|\$|USD|EUR|£|GBP)\s*([\d,]+(?:\.\d{1,2})?)",
    r"([\d,]+(?:\.\d{1,2})?)\s*(?:INR|Rs\.?|₹)",
]
# Pattern group 3 → LOW confidence (bare number, last resort)
_LOW_PATTERNS = [
    r"\b(\d{2,7}(?:\.\d{1,2})?)\b",
]

_CURRENCY_RE = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)", re.IGNORECASE)
_CURRENCY_MAP = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR",
    "$": "USD", "usd": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
}


def extract_amount_with_confidence(text: str) -> tuple[Optional[float], str]:
    """
    Try patterns in order HIGH → MEDIUM → LOW.
    Returns (amount, confidence_level) or (None, 'NONE').
    """
    for pattern in _HIGH_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = _parse_float(m.group(1))
            if val is not None:
                return val, "HIGH"

    for pattern in _MEDIUM_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = _parse_float(m.group(1))
            if val is not None:
                return val, "MEDIUM"

    # LOW: try bare numbers only if a currency word is anywhere in text
    if _CURRENCY_RE.search(text):
        for pattern in _LOW_PATTERNS:
            for m in re.finditer(pattern, text):
                val = _parse_float(m.group(1))
                if val is not None and 1 < val < 1_000_000:
                    return val, "LOW"

    return None, "NONE"


def detect_currency(text: str) -> str:
    m = _CURRENCY_RE.search(text)
    if m:
        key = m.group(1).lower().rstrip(".")
        return _CURRENCY_MAP.get(key, "INR")
    return "INR"


def detect_category(
    sender: str,
    subject: str,
    custom_rules: Optional[list[dict]] = None,
) -> str:
    """
    1. Check custom_rules (user-defined, checked first).
    2. Fall back to built-in CATEGORY_MAP.
    """
    from config.category_map import CATEGORY_MAP

    combined = f"{sender.lower()} {subject.lower()}"

    # Custom rules first
    if custom_rules:
        for rule in custom_rules:
            keyword  = rule.get("keyword", "").lower()
            match_in = rule.get("match_in", "both")
            category = rule.get("category", "Other")
            if not keyword:
                continue
            if match_in == "sender" and keyword in sender.lower():
                return category
            elif match_in == "subject" and keyword in subject.lower():
                return category
            elif keyword in combined:
                return category

    for kw, cat in CATEGORY_MAP.items():
        if kw in combined:
            return cat

    return "Other"


def parse_gmail_message(
    msg: dict,
    custom_rules: Optional[list[dict]] = None,
) -> Optional[dict]:
    """
    Parse a full Gmail API message resource into an expense dict.

    Returns None if:
    - no amount found, OR
    - the classifier determines this is NOT_EXPENSE.

    Sets status='review' and needs_review=1 if the classifier returns REVIEW.
    """
    from config.payment_patterns import detect_payment_method

    payload = msg.get("payload", {})
    headers: dict[str, str] = {
        h["name"].lower(): h["value"]
        for h in payload.get("headers", [])
    }

    subject  = headers.get("subject", "(no subject)")
    from_raw = headers.get("from", "")
    date_raw = headers.get("date", "")
    snippet  = msg.get("snippet", "")
    msg_id   = msg.get("id", "")

    sender_name, sender_email = _parse_from(from_raw)
    email_date = _parse_date(date_raw)
    month = email_date[:7]  # YYYY-MM

    body_text = _extract_body_text(payload)
    search_text = f"{subject} {snippet} {body_text[:3000]}"

    amount, confidence = extract_amount_with_confidence(search_text)
    if amount is None:
        return None

    currency       = detect_currency(search_text)
    method, last4  = detect_payment_method(search_text)
    payment_method = f"{method} ••{last4}" if last4 else method
    category       = detect_category(sender_name + " " + sender_email, subject, custom_rules)

    # ── Classifier pipeline (rules → ML → LLM) ────────────────────────────────
    classification_source = "rules"
    needs_review          = 0
    status                = "active"

    try:
        from classifier import classify, EmailInput
        from classifier.audit import log_classification

        cl_input  = EmailInput(
            subject=subject,
            body=body_text[:3000],
            sender=sender_name or sender_email,
            sender_email=sender_email,
        )
        cl_result = classify(cl_input)

        if cl_result.label == "NOT_EXPENSE":
            logger.debug("Classifier: NOT_EXPENSE — skipping %r", subject)
            return None

        if cl_result.label == "REVIEW":
            status       = "review"
            needs_review = 1

        classification_source = cl_result.stage_used
        log_classification(cl_result, email_id=msg_id)

    except ImportError:
        logger.debug("Classifier not available — using rule-based fallback only")
    except Exception as exc:
        logger.warning("Classifier error for %r: %s — proceeding with active status", subject, exc)

    return {
        "id":                    msg_id,
        "fetch_date":            datetime.utcnow().isoformat(),
        "email_date":            email_date,
        "month":                 month,
        "sender":                sender_name or sender_email,
        "sender_email":          sender_email,
        "subject":               subject,
        "amount":                amount,
        "amount_edited":         None,
        "currency":              currency,
        "payment_method":        payment_method,
        "category":              category,
        "category_edited":       None,
        "tags":                  "[]",
        "confidence":            confidence,
        "status":                status,
        "snippet":               snippet,
        "notes":                 None,
        "classification_source": classification_source,
        "needs_review":          needs_review,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _parse_float(raw: str) -> Optional[float]:
    try:
        val = float(raw.replace(",", ""))
        if 0 < val < 10_000_000:
            return round(val, 2)
    except (ValueError, AttributeError):
        pass
    return None


def _parse_from(from_header: str) -> tuple[str, str]:
    m = re.match(r'^"?([^"<]*)"?\s*<?([^>]+@[^>]+)>?$', from_header.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if "@" in from_header:
        return from_header.strip(), from_header.strip()
    return from_header.strip(), ""


def _parse_date(date_header: str) -> str:
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
    ]
    cleaned = re.sub(r"\s*\([^)]+\)\s*$", "", date_header.strip())
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.today().strftime("%Y-%m-%d")


def _extract_body_text(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data", "")
    if data:
        try:
            text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if "text/html" in mime:
                text = re.sub(r"<[^>]+>", " ", text)
            return text[:10_000]
        except Exception:
            pass
    for part in payload.get("parts", []):
        result = _extract_body_text(part)
        if result:
            return result
    return ""
