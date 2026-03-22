"""
expense_parser.py — Extract monetary amounts and classify expense categories
from Gmail message data (subject, sender, body snippet).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Amount extraction patterns (tried in order) ──────────────────────────────
AMOUNT_PATTERNS: list[str] = [
    # "Total: ₹1,234.56" / "Amount: Rs. 500"
    r"(?:total|amount|paid|charged|price|cost|bill|due|subtotal)\s*[:\-]?\s*"
    r"(?:INR|Rs\.?|₹|\$|USD|EUR|£|GBP)?\s*([\d,]+(?:\.\d{1,2})?)",
    # "₹1,234.56" / "Rs 500" / "$9.99"
    r"(?:INR|Rs\.?|₹|\$|USD|EUR|£|GBP)\s*([\d,]+(?:\.\d{1,2})?)",
    # "1,234.56 INR" / "500 Rs"
    r"([\d,]+(?:\.\d{1,2})?)\s*(?:INR|Rs\.?|₹)",
]

# ── Currency symbol → canonical string ───────────────────────────────────────
CURRENCY_MAP: dict[str, str] = {
    "₹": "INR", "Rs": "INR", "Rs.": "INR", "INR": "INR",
    "$": "USD", "USD": "USD",
    "€": "EUR", "EUR": "EUR",
    "£": "GBP", "GBP": "GBP",
}

_CURRENCY_DETECT = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)", re.IGNORECASE)

# ── Keyword → category map ────────────────────────────────────────────────────
CATEGORY_MAP: dict[str, str] = {
    # Shopping
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping",
    "meesho": "Shopping", "snapdeal": "Shopping", "nykaa": "Shopping",
    "ajio": "Shopping",
    # Food
    "zomato": "Food", "swiggy": "Food", "dominos": "Food",
    "pizza": "Food", "mcdonalds": "Food", "blinkit": "Food",
    "zepto": "Food", "instamart": "Food", "restaurant": "Food",
    # Transport
    "uber": "Transport", "ola": "Transport", "rapido": "Transport",
    "metro": "Transport", "cab": "Transport",
    # Subscriptions
    "netflix": "Subscriptions", "spotify": "Subscriptions",
    "hotstar": "Subscriptions", "prime video": "Subscriptions",
    "youtube premium": "Subscriptions", "zee5": "Subscriptions",
    "apple": "Subscriptions", "google one": "Subscriptions",
    "linkedin": "Subscriptions", "github": "Subscriptions",
    # Utilities
    "electricity": "Utilities", "bescom": "Utilities", "msedcl": "Utilities",
    "water bill": "Utilities", "gas": "Utilities",
    # Telecom
    "airtel": "Telecom", "jio": "Telecom", "vi ": "Telecom",
    "vodafone": "Telecom", "bsnl": "Telecom", "recharge": "Telecom",
    # Healthcare
    "hospital": "Healthcare", "pharmacy": "Healthcare",
    "apollo": "Healthcare", "medplus": "Healthcare",
    "1mg": "Healthcare", "netmeds": "Healthcare", "clinic": "Healthcare",
    # Travel
    "irctc": "Travel", "makemytrip": "Travel", "goibibo": "Travel",
    "yatra": "Travel", "hotel": "Travel", "oyo": "Travel",
    "booking.com": "Travel", "airbnb": "Travel", "indigo": "Travel",
    "airindia": "Travel", "spicejet": "Travel",
    # Insurance
    "insurance": "Insurance", "lic": "Insurance", "hdfc life": "Insurance",
    "icici prudential": "Insurance",
    # Finance
    "emi": "Finance", "loan": "Finance", "credit card": "Finance",
    "bank statement": "Finance", "neft": "Finance", "imps": "Finance",
    "upi": "Finance",
}


@dataclass
class Expense:
    """Represents a single parsed expense entry."""
    date: str               # ISO-format date string "YYYY-MM-DD"
    sender: str
    sender_email: str
    subject: str
    amount: float
    currency: str
    category: str
    snippet: str
    message_id: str
    body_preview: str = field(default="")  # first ~2000 chars of body


def detect_currency(text: str) -> str:
    """Return the first recognised currency symbol found in *text*."""
    m = _CURRENCY_DETECT.search(text)
    if m:
        sym = m.group(1)
        for key, val in CURRENCY_MAP.items():
            if sym.upper().startswith(key.upper()):
                return val
    return "INR"   # default for Indian-focused tracker


def extract_amount(text: str) -> Optional[float]:
    """
    Try each pattern in AMOUNT_PATTERNS against *text*.
    Return the first valid positive float found, or None.
    """
    for pattern in AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(1).replace(",", "")
            try:
                value = float(raw)
                if 0 < value < 10_000_000:   # sanity bounds
                    return round(value, 2)
            except ValueError:
                continue
    return None


def detect_category(sender: str, subject: str) -> str:
    """
    Classify an email into a category using CATEGORY_MAP keyword matching.
    Checks sender domain/address then subject line.
    """
    combined = f"{sender.lower()} {subject.lower()}"
    for keyword, category in CATEGORY_MAP.items():
        if keyword in combined:
            return category
    return "Other"


def parse_gmail_message(msg: dict) -> Optional[Expense]:
    """
    Parse a raw Gmail API message dict into an Expense object.
    Returns None if no monetary amount is detected.

    *msg* is the full message resource with 'payload' included.
    """
    headers: dict[str, str] = {}
    payload = msg.get("payload", {})
    for h in payload.get("headers", []):
        headers[h["name"].lower()] = h["value"]

    subject   = headers.get("subject", "(no subject)")
    from_raw  = headers.get("from", "")
    date_raw  = headers.get("date", "")
    snippet   = msg.get("snippet", "")
    msg_id    = msg.get("id", "")

    # Parse sender name + email
    sender_name, sender_email = _parse_from(from_raw)

    # Normalise date
    date_str = _parse_date(date_raw)

    # Collect text to search for amount
    body_text = _extract_body_text(payload)
    search_text = f"{subject} {snippet} {body_text[:2000]}"

    amount = extract_amount(search_text)
    if amount is None:
        return None   # not an expense email

    currency = detect_currency(search_text)
    category = detect_category(sender_name + " " + sender_email, subject)

    return Expense(
        date=date_str,
        sender=sender_name or sender_email,
        sender_email=sender_email,
        subject=subject,
        amount=amount,
        currency=currency,
        category=category,
        snippet=snippet,
        message_id=msg_id,
        body_preview=body_text[:2000],
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _parse_from(from_header: str) -> tuple[str, str]:
    """Return (display_name, email_address) from a From: header value."""
    m = re.match(r'^"?([^"<]*)"?\s*<?([^>]+@[^>]+)>?$', from_header.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if "@" in from_header:
        return from_header.strip(), from_header.strip()
    return from_header.strip(), ""


def _parse_date(date_header: str) -> str:
    """Convert RFC-2822 date string to 'YYYY-MM-DD'. Returns today on failure."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
    ]
    # Strip trailing parenthetical timezone comments e.g. "(IST)"
    cleaned = re.sub(r"\s*\([^)]+\)\s*$", "", date_header.strip())
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.today().strftime("%Y-%m-%d")


def _extract_body_text(payload: dict) -> str:
    """
    Recursively walk MIME payload parts to find plain-text body.
    Returns decoded text (up to 10 KB for performance).
    """
    import base64

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if body_data:
        try:
            text = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
            if "text/plain" in mime_type or "text/html" in mime_type:
                # Strip basic HTML tags when present
                if "text/html" in mime_type:
                    text = re.sub(r"<[^>]+>", " ", text)
                return text[:10_000]
        except Exception:
            pass

    # Walk multipart parts
    for part in payload.get("parts", []):
        result = _extract_body_text(part)
        if result:
            return result

    return ""
