#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"
TRAINING_CSV = DATA_DIR / "training_emails.csv"


def analyze_training_data(csv_path: Path = TRAINING_CSV) -> dict:
    """Analyze training data and return statistics."""
    rows = []
    label_counts = Counter()
    sender_counts = Counter()
    expense_keywords = [
        "invoice", "bill", "payment", "receipt", "order", "transaction",
        "charge", "deducted", "debited", "paid", "subscription", "renewal",
        "emi", "booking", "purchase", "buy", "recharge"
    ]
    
    non_expense_patterns = [
        "team", "meeting", "happy", "birthday", "newsletter", "digest",
        "social", "notification", "mention", "liked", "comment", "invite",
        "welcome", "reminder", "survey", "party", "outing", "annual day",
        "job application", "performance review", "leave application",
        "project", "kickoff", "sprint", "code review", "training",
        "maintenance", "warranty", "policy", "invitation", "greeting",
        "festival", "blood donation", "reunion", "recipe", "podcast"
    ]
    
    hr_senders = ["hr@", "hrs@"]
    social_senders = [
        "notification@linkedin.com", "noreply@whatsapp.com",
        "notification@instagram.com", "notifications@slack.com",
        "notifications@github.com", "notifications@x.com",
        "notifications@youtube.com", "invitations@linkedin.com"
    ]
    system_senders = [
        "security@", "support@", "admin@", "monitoring@",
        "drive-noreply@", "cloud@"
    ]
    
    issues = {
        "salary_credits": [],
        "credit_card_bills_misclassified": [],
        "non_transactional_labeled_expense": [],
        "non_transactional_samples": [],
        "marketing_promotional": [],
        "hr_internal": [],
        "social_media": [],
        "system_alerts": []
    }
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 2):
            rows.append(row)
            label_counts[row["label"]] += 1
            sender_counts[row["sender"]] += 1
            
            subject_lower = row["subject"].lower()
            body_lower = row["body"].lower()
            sender_lower = row["sender"].lower()
            text = f"{subject_lower} {body_lower}"
            
            if row["label"] == "EXPENSE":
                if "salary" in text or "credited" in text and "salary" in text:
                    issues["salary_credits"].append(idx)
                
                if any(pattern in text for pattern in non_expense_patterns):
                    if not any(kw in text for kw in ["payment", "charge", "invoice", "bill"]):
                        issues["non_transactional_labeled_expense"].append(idx)
            
            else:
                if "credit card" in text and "bill" in text and "due" in text:
                    issues["credit_card_bills_misclassified"].append(idx)
                
                if any(pattern in text for pattern in non_expense_patterns):
                    issues["non_transactional_samples"].append(idx)
                    if "sale" in text or "off" in text or "deal" in text:
                        issues["marketing_promotional"].append(idx)
                    if any(s in sender_lower for s in hr_senders):
                        issues["hr_internal"].append(idx)
                    if any(s in sender_lower for s in social_senders):
                        issues["social_media"].append(idx)
                    if any(s in sender_lower for s in system_senders):
                        issues["system_alerts"].append(idx)
    
    total = len(rows)
    expense_count = label_counts["EXPENSE"]
    not_expense_count = label_counts["NOT_EXPENSE"]
    
    return {
        "total_samples": total,
        "expense_samples": expense_count,
        "not_expense_samples": not_expense_count,
        "balance_percentage": f"{(expense_count / total) * 100:.1f}%",
        "label_distribution": dict(label_counts),
        "top_senders": sender_counts.most_common(10),
        "unique_senders": len(sender_counts),
        "issues": issues
    }


def print_analysis_report(stats: dict) -> None:
    """Print formatted analysis report."""
    print("\n" + "=" * 60)
    print("TRAINING DATA ANALYSIS REPORT")
    print("=" * 60)
    
    print(f"\n📊 Total Samples: {stats['total_samples']}")
    print(f"   EXPENSE: {stats['expense_samples']} ({stats['balance_percentage']})")
    print(f"   NOT_EXPENSE: {stats['not_expense_samples']}")
    print(f"   Unique Senders: {stats['unique_senders']}")
    
    print("\n📈 Top 10 Senders:")
    for idx, (sender, count) in enumerate(stats["top_senders"], 1):
        print(f"   {idx}. {sender}: {count} emails")
    
    issues = stats["issues"]
    
    print("\n⚠️  DATA QUALITY ISSUES:")
    
    if issues["salary_credits"]:
        print(f"\n   1. Salary Credits Misclassified as EXPENSE: {len(issues['salary_credits'])}")
        print(f"      Rows: {issues['salary_credits']}")
    
    if issues["credit_card_bills_misclassified"]:
        print(f"\n   2. Credit Card Bills Misclassified as NOT_EXPENSE: {len(issues['credit_card_bills_misclassified'])}")
        print(f"      Rows: {issues['credit_card_bills_misclassified']}")
    
    if issues["non_transactional_labeled_expense"]:
        print(f"\n   3. Non-Transactional Emails Labeled as EXPENSE: {len(issues['non_transactional_labeled_expense'])}")
        print(f"      Rows: {issues['non_transactional_labeled_expense']}")
    
    if issues["non_transactional_samples"]:
        print(f"\n   4. Non-Transactional Samples (should be reviewed): {len(issues['non_transactional_samples'])}")
        print(f"      Marketing/Promotional: {len(issues['marketing_promotional'])}")
        print(f"      HR/Internal: {len(issues['hr_internal'])}")
        print(f"      Social Media: {len(issues['social_media'])}")
        print(f"      System Alerts: {len(issues['system_alerts'])}")
    
    total_issues = (
        len(issues["salary_credits"]) +
        len(issues["credit_card_bills_misclassified"]) +
        len(issues["non_transactional_labeled_expense"]) +
        len(issues["non_transactional_samples"])
    )
    
    print(f"\n📋 SUMMARY:")
    print(f"   Total Issues Found: {total_issues}")
    print(f"   High Priority Fixes: {len(issues['salary_credits']) + len(issues['credit_card_bills_misclassified'])}")
    print(f"   Medium Priority (non-transactional): {len(issues['non_transactional_samples'])}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    stats = analyze_training_data()
    print_analysis_report(stats)
