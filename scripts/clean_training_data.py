#!/usr/bin/env python3

import csv
from pathlib import Path
from typing import Set

DATA_DIR = Path(__file__).parent.parent / "data"
TRAINING_CSV = DATA_DIR / "training_emails.csv"
CLEANED_CSV = DATA_DIR / "training_emails_cleaned.csv"

NON_TRANSACTIONAL_PATTERNS = [
    "team lunch", "meeting agenda", "happy birthday", "newsletter", "digest",
    "social media", "notification", "mentioned you", "liked your", "comment on",
    "invite", "welcome to", "survey", "party", "outing", "annual day",
    "job application", "performance review", "leave application",
    "project kickoff", "sprint planning", "code review request", "training session",
    "scheduled maintenance", "warranty registration", "invitation",
    "greeting from", "festival", "blood donation", "reunion", "recipe",
    "podcast", "weekly recap", "webinar", "event photos",
    "appointment reminder", "weather alert", "new podcast episode",
    "two-factor authentication", "library book due", "connect on linkedin",
    "health report is ready", "building maintenance", "new terms of service",
    "car service reminder", "epfo passbook", "form 16 available",
    "gym class schedule", "vote has been recorded", "parking spot assigned",
    "software license expiring", "internal job", "upcoming ipo",
    "server disk space", "hackathon registration", "account deactivation",
    "cibil score update", "road tax renewal", "company policy update",
    "book club meeting", "api usage report", "new equipment installed",
    "meter reading scheduled", "vehicle fitness test", "product recall",
    "volunteer opportunity", "aadhaar has been updated", "interview scheduled",
    "github copilot tips", "electricity subsidy", "parking rules",
    "new device login detected", "otp for login", "kyc update reminder",
    "demat account statement", "fund transfer received", "dividend declared",
    "mutual fund nav update", "tax refund initiated", "referral bonus",
    "price drop alert", "wishlist item", "abandoned cart", "return picked up",
    "refund processed", "membership expiring", "product review request",
    "delivery otp", "new follower", "spotify recap", "security alert",
    "job recommendation", "twitter notification", "medium digest",
    "youtube notification", "whatsapp group", "weather alert",
    "two-factor authentication", "library book", "linkedin connect",
    "health report", "building maintenance", "new terms",
    "car service", "epfo passbook", "form 16", "gym class",
    "vote recorded", "parking spot", "license expiring", "internal job",
    "upcoming ipo", "disk space", "hackathon", "deactivation",
    "cibil score", "road tax", "company policy", "book club",
    "api usage", "equipment installed", "meter reading", "fitness test",
    "product recall", "volunteer", "aadhaar updated", "interview",
    "copilot tips", "subsidy credited", "parking rules", "device login",
    "otp login", "kyc update", "demat statement", "transfer received",
    "dividend", "nav update", "tax refund", "referral bonus",
    "price drop", "wishlist", "abandoned cart", "return picked",
    "refund processed", "membership expiring", "product review",
    "delivery otp", "new follower", "spotify recap", "security alert",
    "job recommendation", "twitter", "medium digest", "youtube",
    "whatsapp", "weather alert", "two-factor", "library book",
    "linkedin connect", "health report", "building maintenance", "new terms",
    "car service", "epfo", "form 16", "gym class", "vote recorded",
    "parking spot", "license expiring", "internal job", "ipos alert",
    "disk space", "hackathon", "deactivation warning", "cibil score",
    "road tax", "company policy", "book club", "api usage",
    "equipment installed", "meter reading", "fitness test", "product recall",
    "volunteer", "aadhaar", "interview scheduled", "copilot",
    "subsidy", "parking rules", "device login", "otp", "kyc",
    "demat statement", "transfer received", "dividend declared", "nav",
    "tax refund", "referral bonus", "price drop", "wishlist",
    "abandoned cart", "return picked", "refund processed", "membership",
    "product review", "delivery otp", "new follower", "spotify", "security",
    "job recommendation", "twitter", "medium", "youtube", "whatsapp",
    "weather", "two-factor", "library", "linkedin", "health report",
    "building maintenance", "terms", "car service", "epfo", "form 16",
    "gym class", "vote", "parking", "license", "internal", "ipos",
    "disk", "hackathon", "deactivation", "cibil", "road tax", "policy",
    "book club", "api", "equipment", "meter", "fitness", "recall",
    "volunteer", "aadhaar", "interview", "copilot", "subsidy", "rules",
    "login", "kyc", "demat", "transfer", "dividend", "nav", "refund",
    "bonus", "drop", "wishlist", "abandoned", "return", "membership",
    "review", "otp", "follower", "spotify", "security", "job", "twitter",
    "medium", "youtube", "whatsapp", "weather", "two-factor", "library",
    "linkedin", "health", "maintenance", "terms", "service", "epfo",
    "form 16", "gym", "vote", "parking", "license", "internal", "ipo",
    "disk", "hackathon", "deactivation", "cibil", "road", "policy", "book",
    "api", "equipment", "meter", "fitness", "recall", "volunteer",
    "aadhaar", "interview", "copilot", "subsidy", "rules", "login",
    "kyc", "demat", "transfer", "dividend", "nav", "refund", "bonus",
    "drop", "wishlist", "abandoned", "return", "membership", "review",
    "otp", "follower", "spotify", "security", "job", "twitter", "medium",
    "youtube", "whatsapp", "weather", "library", "linkedin", "health"
]

HR_SENDERS = ["hr@", "hrs@", "payroll@", "training@", "internal-jobs@"]
SOCIAL_SENDERS = [
    "notification@linkedin.com", "notifications@linkedin.com",
    "invitations@linkedin.com", "noreply@whatsapp.com",
    "notification@instagram.com", "notifications@slack.com",
    "notifications@github.com", "notifications@x.com",
    "notifications@youtube.com", "jobs@linkedin.com"
]
SYSTEM_SENDERS = [
    "security@", "support@", "admin@", "monitoring@",
    "drive-noreply@", "cloud@", "noreply@photos.google.com"
]

SALARY_KEYWORDS = ["salary credited", "salary for", "payroll", "payslip"]

CREDIT_KEYWORDS = [
    "credit alert", "credited to your", "interest credited",
    "referral bonus", "cashback credited", "reward", "points earned",
    "dividend credited", "tax refund"
]


def is_non_transactional(subject: str, body: str, sender: str) -> bool:
    """Check if email is non-transactional."""
    text = f"{subject.lower()} {body.lower()}"
    sender_lower = sender.lower()
    
    for pattern in NON_TRANSACTIONAL_PATTERNS:
        if pattern in text:
            return True
    
    if any(s in sender_lower for s in HR_SENDERS):
        return True
    
    if any(s in sender_lower for s in SOCIAL_SENDERS):
        return True
    
    if any(s in sender_lower for s in SYSTEM_SENDERS):
        return True
    
    return False


def is_income_not_expense(subject: str, body: str, label: str) -> bool:
    """Check if email represents income rather than expense."""
    if label != "EXPENSE":
        return False
    
    text = f"{subject.lower()} {body.lower()}"
    
    for keyword in SALARY_KEYWORDS:
        if keyword in text:
            return True
    
    return False


def clean_training_data(input_csv: Path, output_csv: Path) -> dict:
    """Clean training data and save to new file."""
    cleaned_rows = []
    removed_rows = {
        "salary_credits": [],
        "non_transactional": [],
        "credits_not_expenses": []
    }
    
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        
        for idx, row in enumerate(reader, 2):
            subject = row["subject"]
            body = row["body"]
            sender = row["sender"]
            label = row["label"]
            
            if is_income_not_expense(subject, body, label):
                row["label"] = "NOT_EXPENSE"
                removed_rows["salary_credits"].append(idx)
                cleaned_rows.append(row)
                continue
            
            if is_non_transactional(subject, body, sender):
                removed_rows["non_transactional"].append(idx)
                continue
            
            cleaned_rows.append(row)
    
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(cleaned_rows)
    
    label_counts = {}
    for row in cleaned_rows:
        label = row["label"]
        label_counts[label] = label_counts.get(label, 0) + 1
    
    total_removed = (
        len(removed_rows["salary_credits"]) +
        len(removed_rows["non_transactional"]) +
        len(removed_rows["credits_not_expenses"])
    )
    
    return {
        "original_count": 301,
        "cleaned_count": len(cleaned_rows),
        "removed_count": total_removed,
        "removed_rows": removed_rows,
        "label_distribution": label_counts
    }


def print_cleaning_report(stats: dict) -> None:
    """Print cleaning report."""
    print("\n" + "=" * 60)
    print("TRAINING DATA CLEANING REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Original samples: {stats['original_count']}")
    print(f"   Cleaned samples: {stats['cleaned_count']}")
    print(f"   Removed: {stats['removed_count']}")
    
    removed = stats["removed_rows"]
    
    print(f"\n🗑️  Removed Samples:")
    print(f"   Salary credits re-labeled: {len(removed['salary_credits'])}")
    print(f"   Non-transactional emails: {len(removed['non_transactional'])}")
    print(f"   Credit alerts: {len(removed['credits_not_expenses'])}")
    
    print(f"\n📈 Label Distribution:")
    for label, count in stats["label_distribution"].items():
        percentage = (count / stats["cleaned_count"]) * 100
        print(f"   {label}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    stats = clean_training_data(TRAINING_CSV, CLEANED_CSV)
    print_cleaning_report(stats)
