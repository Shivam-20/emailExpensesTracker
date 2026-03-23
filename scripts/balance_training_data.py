#!/usr/bin/env python3

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CLEANED_CSV = DATA_DIR / "training_emails_cleaned.csv"
BALANCED_CSV = DATA_DIR / "training_emails.csv"

NEW_NOT_EXPENSE_SAMPLES = [
    ["Weekly newsletter: Tech trends", "This week in technology: AI breakthroughs, new gadgets, and industry news. Read more on our blog.", "newsletter@techweekly.com", "NOT_EXPENSE"],
    ["Your order has shipped", "Your Amazon order #123-456789 has been shipped. Track your package with the link below.", "shipping@amazon.in", "NOT_EXPENSE"],
    ["Welcome to our community", "Welcome! We're excited to have you join our community. Complete your profile to get started.", "welcome@community.com", "NOT_EXPENSE"],
    ["Password reset link", "Someone requested a password reset for your account. Click here if this was you.", "security@app.com", "NOT_EXPENSE"],
    ["New feature announcement", "We've launched a new feature! Watch our video tutorial to learn how it works.", "product@company.com", "NOT_EXPENSE"],
    ["Survey invitation", "Help us improve! Take our 2-minute survey about your recent experience.", "survey@feedback.com", "NOT_EXPENSE"],
    ["Event reminder: Webinar tomorrow", "Don't forget! Join our webinar on Industry Trends tomorrow at 3 PM IST.", "events@webinar.com", "NOT_EXPENSE"],
    ["Your subscription is active", "Your free subscription is active. Upgrade to premium for more features.", "info@service.com", "NOT_EXPENSE"],
    ["New blog post published", "New article: '10 Tips for Productivity'. Read it now on our blog.", "blog@company.com", "NOT_EXPENSE"],
    ["Account verification needed", "Please verify your email address to continue using our service.", "verify@app.com", "NOT_EXPENSE"],
    ["Job opportunity alert", "Based on your profile, we found 3 job openings that match your skills.", "jobs@careers.com", "NOT_EXPENSE"],
    ["System maintenance notice", "Scheduled maintenance on Sunday 2-4 AM. Services may be temporarily unavailable.", "admin@platform.com", "NOT_EXPENSE"],
    ["Weekly digest: Top stories", "Top 5 stories this week: Technology, Business, and more. Click to read.", "digest@news.com", "NOT_EXPENSE"],
    ["Your profile was viewed", "Your LinkedIn profile was viewed by 5 recruiters this week.", "notifications@linkedin.com", "NOT_EXPENSE"],
    ["New follower on social media", "You have a new follower! Check out their profile.", "notification@social.com", "NOT_EXPENSE"],
    ["Review your recent activity", "Here's your weekly activity summary on our platform.", "summary@service.com", "NOT_EXPENSE"],
    ["Invite: Company town hall", "Join us for the Q1 company town hall meeting this Friday at 4 PM.", "events@company.com", "NOT_EXPENSE"],
    ["Free course available", "Enroll in our free course: 'Introduction to Data Science'. Limited spots available.", "courses@learning.com", "NOT_EXPENSE"],
    ["Your feedback is valuable", "Thank you for your feedback! We've incorporated your suggestions.", "support@service.com", "NOT_EXPENSE"],
    ["Podcast episode released", "New episode: 'The Future of Work' is now available. Listen now!", "podcast@studio.com", "NOT_EXPENSE"],
    ["Update your preferences", "Manage your email preferences. Choose which updates you want to receive.", "preferences@mailer.com", "NOT_EXPENSE"],
    ["Happy holidays from the team", "Wishing you and your family a happy holiday season!", "greetings@company.com", "NOT_EXPENSE"],
    ["You're invited: Beta program", "Join our exclusive beta program and get early access to new features.", "beta@product.com", "NOT_EXPENSE"],
    ["Security alert: New login", "We detected a new login to your account from a new device. Was this you?", "security@platform.com", "NOT_EXPENSE"],
    ["Your report is ready", "Your monthly report is ready to download. Click the link below.", "reports@analytics.com", "NOT_EXPENSE"],
    ["Community guidelines updated", "We've updated our community guidelines. Please review the changes.", "policy@platform.com", "NOT_EXPENSE"],
    ["New product announcement", "Introducing our latest product! Learn more about its features.", "launch@company.com", "NOT_EXPENSE"],
    ["Meeting scheduled", "Your meeting with the sales team is scheduled for Tuesday at 2 PM.", "calendar@company.com", "NOT_EXPENSE"],
    ["Account expiration warning", "Your account will expire in 30 days. Renew now to continue using our service.", "billing@service.com", "NOT_EXPENSE"],
    ["You've been mentioned", "Someone mentioned you in a comment. Click to view.", "notification@platform.com", "NOT_EXPENSE"],
    ["Weekly goals update", "Here's your weekly goals progress. You're on track!", "goals@productivity.com", "NOT_EXPENSE"],
    ["New badge earned", "Congratulations! You've earned the 'Early Adopter' badge.", "achievements@platform.com", "NOT_EXPENSE"],
    ["Support ticket resolved", "Your support ticket #12345 has been resolved. Let us know if you need more help.", "support@company.com", "NOT_EXPENSE"],
    ["Invitation: Team event", "You're invited to our team building event next Friday at 5 PM.", "events@company.com", "NOT_EXPENSE"],
    ["Your data export is ready", "Your data export request is complete. Download your file before it expires.", "data@platform.com", "NOT_EXPENSE"],
    ["New feature: Dark mode", "Dark mode is now available! Update your settings to try it out.", "product@company.com", "NOT_EXPENSE"],
    ["Quarterly newsletter", "Q1 Newsletter: Top highlights and updates from our team.", "newsletter@company.com", "NOT_EXPENSE"],
    ["Your subscription will expire", "Your subscription expires in 7 days. Renew to continue uninterrupted service.", "renewal@service.com", "NOT_EXPENSE"],
    ["Weekly challenge started", "This week's challenge: Complete 5 tasks. Win exclusive rewards!", "challenges@platform.com", "NOT_EXPENSE"],
    ["API documentation updated", "We've updated our API documentation with new endpoints and examples.", "docs@developer.com", "NOT_EXPENSE"],
    ["You're trending!", "Your post is trending! It has received 500+ views in the last hour.", "notification@platform.com", "NOT_EXPENSE"],
    ["Learning path recommended", "Based on your interests, we recommend the 'Data Science' learning path.", "recommendations@learning.com", "NOT_EXPENSE"],
    ["Free trial extension", "We've extended your free trial by 7 days. Enjoy exploring!", "promo@service.com", "NOT_EXPENSE"],
    ["Your question was answered", "Your question on the community forum has been answered by an expert.", "forum@community.com", "NOT_EXPENSE"],
    ["New connection request", "You have a new connection request on our professional network.", "network@platform.com", "NOT_EXPENSE"],
    ["Weekly leaderboard updated", "Check out this week's top performers. Are you on the list?", "leaderboard@platform.com", "NOT_EXPENSE"],
    ["Your wishlist has a price drop", "An item in your wishlist is now 20% off. Limited time offer!", "deals@shopping.com", "NOT_EXPENSE"],
    ["Conference registration open", "Register for our annual conference. Early bird discounts available.", "events@conference.com", "NOT_EXPENSE"],
    ["Your session was saved", "Your work session was automatically saved. No data lost.", "system@productivity.com", "NOT_EXPENSE"],
    ["New template available", "We've added 5 new templates to help you work faster. Try them now!", "templates@productivity.com", "NOT_EXPENSE"],
    ["Achievement unlocked", "You've unlocked a new achievement: '100 Day Streak'. Keep it up!", "achievements@platform.com", "NOT_EXPENSE"],
    ["Monthly summary ready", "Your monthly activity summary is ready. View your progress and insights.", "summary@platform.com", "NOT_EXPENSE"],
    ["You've been featured", "Your work has been featured in our 'Spotlight' section this week!", "editorial@platform.com", "NOT_EXPENSE"],
    ["New collaboration tools", "Explore our new collaboration features for teams. Work together seamlessly.", "product@company.com", "NOT_EXPENSE"],
    ["Your feedback helped improve us", "Thanks to your feedback, we've improved our service. Here's what's new.", "product@company.com", "NOT_EXPENSE"],
    ["Upcoming webinar series", "Join our 3-part webinar series on industry trends. Free registration.", "webinars@learning.com", "NOT_EXPENSE"],
    ["Your storage is almost full", "Your cloud storage is 90% full. Upgrade now for more space.", "storage@cloud.com", "NOT_EXPENSE"],
    ["New mobile app update", "Version 2.5 is now available. Download for bug fixes and new features.", "app@company.com", "NOT_EXPENSE"],
    ["You're on a winning streak", "You've won 5 challenges in a row! Keep up the great work.", "challenges@platform.com", "NOT_EXPENSE"],
    ["Invitation: User group meetup", "Join our local user group meetup this Saturday. Network and learn!", "meetups@community.com", "NOT_EXPENSE"],
    ["Your insights were shared", "Your insights were shared in our weekly newsletter. Thanks for contributing!", "newsletter@platform.com", "NOT_EXPENSE"],
    ["New integration available", "We've added integration with popular apps. Connect your accounts now.", "integrations@platform.com", "NOT_EXPENSE"],
    ["Your contribution was appreciated", "Your contribution to our open source project has been appreciated by the community.", "opensource@company.com", "NOT_EXPENSE"],
    ["Weekly goals completed", "Congratulations! You've completed all your weekly goals.", "goals@productivity.com", "NOT_EXPENSE"],
    ["New learning resources", "We've added 20 new tutorials to our learning center. Start learning today!", "learning@education.com", "NOT_EXPENSE"],
    ["Your profile is complete", "Your profile is now 100% complete! You're all set to get started.", "onboarding@platform.com", "NOT_EXPENSE"],
    ["Security best practices", "Read our latest article on security best practices to protect your account.", "security@platform.com", "NOT_EXPENSE"],
    ["You've reached a milestone", "Congratulations! You've completed 100 tasks on our platform.", "milestones@platform.com", "NOT_EXPENSE"],
    ["New feature request received", "Thank you for your feature request! We've added it to our roadmap.", "feedback@company.com", "NOT_EXPENSE"],
    ["Weekly digest: Community highlights", "Top community posts this week. Join the conversation!", "digest@community.com", "NOT_EXPENSE"],
    ["Your subscription is active", "Your annual subscription is active until December 2026.", "subscription@service.com", "NOT_EXPENSE"],
    ["New research paper published", "Our team published a new research paper on AI ethics. Read the abstract.", "research@company.com", "NOT_EXPENSE"],
    ["You're invited: Beta testing", "Be among the first to test our new features. Join the beta program.", "beta@product.com", "NOT_EXPENSE"],
    ["Your workspace is ready", "Your new workspace has been created. Start collaborating with your team.", "workspace@platform.com", "NOT_EXPENSE"],
    ["Weekly tips for productivity", "Here are 5 tips to boost your productivity this week.", "tips@productivity.com", "NOT_EXPENSE"],
    ["New podcast episode", "Episode 42: 'Building Great Teams' is now available. Listen on your favorite app.", "podcast@studio.com", "NOT_EXPENSE"],
    ["Your question was featured", "Your question on our Q&A forum has been featured this week.", "forum@community.com", "NOT_EXPENSE"],
    ["Achievement unlocked: First contribution", "Congratulations on your first contribution to our community!", "achievements@platform.com", "NOT_EXPENSE"],
    ["New collaboration features", "We've launched real-time collaboration. Work together with your team.", "product@company.com", "NOT_EXPENSE"],
    ["Your progress report is ready", "View your monthly progress report with detailed analytics.", "reports@platform.com", "NOT_EXPENSE"],
    ["Weekly challenge winner", "Congratulations! You're this week's challenge winner.", "challenges@platform.com", "NOT_EXPENSE"],
    ["New integration with popular tools", "We've added integration with Slack, Teams, and Zoom. Connect now!", "integrations@platform.com", "NOT_EXPENSE"],
    ["Your feedback made a difference", "Your feedback led to 3 new features in our latest update.", "product@company.com", "NOT_EXPENSE"],
    ["Invitation: Virtual meetup", "Join our virtual meetup this Thursday. Topic: Industry Trends.", "events@community.com", "NOT_EXPENSE"],
    ["Your content was shared", "Your content has been shared 100+ times this week. Great job!", "viral@platform.com", "NOT_EXPENSE"],
    ["New learning path: Advanced", "We've launched an advanced learning path for experienced users.", "learning@education.com", "NOT_EXPENSE"],
    ["Your streak continues", "You're on a 30-day streak! Keep the momentum going.", "streak@platform.com", "NOT_EXPENSE"],
    ["New community guidelines", "We've updated our community guidelines. Please review before posting.", "policy@community.com", "NOT_EXPENSE"],
    ["Your subscription will renew", "Your subscription will automatically renew on April 1. Cancel if needed.", "billing@service.com", "NOT_EXPENSE"],
    ["You've earned a badge", "You've earned the 'Community Helper' badge. Wear it with pride!", "achievements@platform.com", "NOT_EXPENSE"],
    ["New feature announcement", "We've launched dark mode across all our apps. Update now to try it!", "launch@company.com", "NOT_EXPENSE"],
    ["Your workspace settings", "Review and update your workspace settings for better collaboration.", "settings@platform.com", "NOT_EXPENSE"],
    ["Weekly digest: Top creators", "Meet our top creators this week. Get inspired by their work.", "digest@community.com", "NOT_EXPENSE"],
    ["New API endpoints", "We've added 10 new API endpoints to our developer portal.", "docs@developer.com", "NOT_EXPENSE"],
    ["Your account security", "Review your account security settings. 2FA is recommended.", "security@platform.com", "NOT_EXPENSE"],
    ["You've been recommended", "Our algorithm recommends checking out these trending posts.", "recommendations@platform.com", "NOT_EXPENSE"],
    ["New templates library", "Browse our expanded templates library with 50+ new designs.", "templates@productivity.com", "NOT_EXPENSE"],
    ["Your weekly achievements", "Here are your achievements for this week. You're doing great!", "achievements@platform.com", "NOT_EXPENSE"],
    ["New integration announced", "We've partnered with leading cloud providers. Integrate now!", "partnerships@company.com", "NOT_EXPENSE"],
    ["Your content performance", "Your content has performed 20% better this week. Keep it up!", "analytics@platform.com", "NOT_EXPENSE"],
    ["New community event", "Join our monthly community showcase. Present your work!", "events@community.com", "NOT_EXPENSE"],
    ["Your subscription benefits", "Explore all the benefits included in your subscription.", "benefits@service.com", "NOT_EXPENSE"],
    ["Weekly challenge: Creative", "This week's creative challenge: Design a logo. Submit your entry!", "challenges@platform.com", "NOT_EXPENSE"],
    ["New feature: Voice notes", "You can now add voice notes to your projects. Try it out!", "product@company.com", "NOT_EXPENSE"],
    ["Your network is growing", "You've gained 25 new followers this week. Expand your reach!", "network@platform.com", "NOT_EXPENSE"],
    ["New research publication", "Our research team published a paper on machine learning. Read now.", "research@company.com", "NOT_EXPENSE"],
    ["Your privacy settings", "Review and update your privacy settings. Your data matters to us.", "privacy@platform.com", "NOT_EXPENSE"],
    ["Weekly newsletter: Innovation", "This week's focus: Innovation in tech. Read the latest insights.", "newsletter@techweekly.com", "NOT_EXPENSE"],
]


def add_not_expense_samples(input_csv: Path, output_csv: Path, samples: list[list]) -> dict:
    """Add new NOT_EXPENSE samples to balance the dataset."""
    existing_rows = []
    
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing_rows.append(row)
    
    for sample in samples:
        row_dict = {
            "subject": sample[0],
            "body": sample[1],
            "sender": sample[2],
            "label": sample[3]
        }
        existing_rows.append(row_dict)
    
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
    
    label_counts = {}
    for row in existing_rows:
        label = row["label"]
        label_counts[label] = label_counts.get(label, 0) + 1
    
    return {
        "original_count": len(existing_rows) - len(samples),
        "added_count": len(samples),
        "final_count": len(existing_rows),
        "label_distribution": label_counts
    }


def print_balance_report(stats: dict) -> None:
    """Print balance report."""
    print("\n" + "=" * 60)
    print("TRAINING DATA BALANCE REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Original count: {stats['original_count']}")
    print(f"   Added samples: {stats['added_count']}")
    print(f"   Final count: {stats['final_count']}")
    
    print(f"\n📈 Label Distribution:")
    for label, count in stats["label_distribution"].items():
        percentage = (count / stats["final_count"]) * 100
        print(f"   {label}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    stats = add_not_expense_samples(CLEANED_CSV, BALANCED_CSV, NEW_NOT_EXPENSE_SAMPLES)
    print_balance_report(stats)
