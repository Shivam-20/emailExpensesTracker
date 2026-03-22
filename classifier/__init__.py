"""
classifier/__init__.py — Public API for the email expense classifier.

Usage:
    from classifier import classify, EmailInput

    result = classify(EmailInput(
        subject="Invoice #4521",
        body="INR 4500 payment received.",
        sender="billing@vendor.com",
    ))
    print(result.label)   # EXPENSE / NOT_EXPENSE / REVIEW
"""

from .router import classify
from .schemas import ClassificationResult, EmailInput

__all__ = ["classify", "ClassificationResult", "EmailInput"]
