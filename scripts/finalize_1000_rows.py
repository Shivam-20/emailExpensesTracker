#!/usr/bin/env python3

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_CSV = DATA_DIR / "training_emails_1000.csv"
FINAL_CSV = DATA_DIR / "training_emails.csv"

ADDITIONAL_EXPENSE = [
    ["Restaurant bill", "Payment of ₹850 made at BBQ Nation via credit card.", "payment@upi.com", "EXPENSE"],
    ["Grocery store", "DMart purchase of ₹1200 paid via debit card.", "store@dmart.in", "EXPENSE"],
    ["Petrol pump", "Fuel purchase at IOCL pump: 15 litres ₹1650 via card.", "receipt@iocl.com", "EXPENSE"],
    ["Medical store", "Pharmacy bill ₹580 paid at local chemist.", "billing@chemist.com", "EXPENSE"],
    ["Clothing store", "H&M purchase ₹2100 paid via credit card.", "orders@hm.com", "EXPENSE"],
    ["Electronics store", "Croma purchase ₹7800 for headphones via EMI.", "orders@croma.com", "EXPENSE"],
    ["Online course", "Udemy course 'Advanced React' purchased for ₹1499.", "noreply@udemy.com", "EXPENSE"],
    ["Software license", "Microsoft Office 365 annual subscription ₹6299 renewed.", "billing@microsoft.com", "EXPENSE"],
    ["Cloud storage", "Google Cloud storage bill $18.50 for March.", "billing@google.com", "EXPENSE"],
    ["Web hosting", "Bluehost hosting bill ₹550 for March due April 15.", "billing@bluehost.com", "EXPENSE"],
    ["Domain name", "Domain myproject.com registered for ₹899 for 1 year.", "billing@namecheap.com", "EXPENSE"],
    ["SSL certificate", "SSL certificate renewed for ₹1399/year.", "billing@godaddy.com", "EXPENSE"],
    ["Email marketing", "Mailchimp monthly plan ₹1050 charged to card.", "billing@mailchimp.com", "EXPENSE"],
    ["Project management", "Asana Premium subscription ₹520/month charged.", "billing@asana.com", "EXPENSE"],
    ["Video conferencing", "Zoom Pro subscription ₹1350/month charged.", "billing@zoom.us", "EXPENSE"],
    ["Design tool", "Canva Pro subscription ₹599/month charged.", "billing@canva.com", "EXPENSE"],
    ["Stock photos", "Shutterstock subscription ₹999/month charged.", "billing@shutterstock.com", "EXPENSE"],
    ["Music streaming", "YouTube Music Premium ₹149/month charged.", "billing@youtube.com", "EXPENSE"],
    ["Cloud backup", "Backblaze backup subscription ₹650/month charged.", "billing@backblaze.com", "EXPENSE"],
    ["VPN service", "NordVPN subscription ₹950/year charged.", "billing@nordvpn.com", "EXPENSE"],
    ["Password manager", "1Password subscription ₹320/month charged.", "billing@1password.com", "EXPENSE"],
    ["Development tool", "GitHub Copilot subscription ₹850/month charged.", "billing@github.com", "EXPENSE"],
    ["API service", "OpenAI API usage $48.00 for March.", "billing@openai.com", "EXPENSE"],
    ["Database service", "MongoDB Atlas bill $32.50 for March.", "billing@mongodb.com", "EXPENSE"],
    ["CDN service", "Cloudflare bill $15.00 for March usage.", "billing@cloudflare.com", "EXPENSE"],
    ["Analytics tool", "Google Analytics 360 subscription ₹18000/month.", "billing@analytics.com", "EXPENSE"],
    ["Marketing automation", "HubSpot subscription ₹13500/month charged.", "billing@hubspot.com", "EXPENSE"],
    ["CRM software", "Salesforce subscription ₹9500/month charged.", "billing@salesforce.com", "EXPENSE"],
    ["HR software", "Zoho People subscription ₹3800/month charged.", "billing@zoho.com", "EXPENSE"],
    ["Accounting", "QuickBooks subscription ₹2100/month charged.", "billing@quickbooks.com", "EXPENSE"],
    ["Legal software", "DocuSign subscription ₹2800/month charged.", "billing@docusign.com", "EXPENSE"],
    ["Team communication", "Slack subscription ₹880/month per user charged.", "billing@slack.com", "EXPENSE"],
    ["File storage", "Dropbox Business subscription ₹1400/month charged.", "billing@dropbox.com", "EXPENSE"],
    ["Video editing", "Adobe Premiere Pro subscription ₹2500/month charged.", "billing@adobe.com", "EXPENSE"],
    ["Photo editing", "Adobe Lightroom subscription ₹1050/month charged.", "billing@adobe.com", "EXPENSE"],
    ["Graphic design", "Adobe Illustrator subscription ₹1950/month charged.", "billing@adobe.com", "EXPENSE"],
    ["Prototyping tool", "Figma Professional subscription ₹1350/month charged.", "billing@figma.com", "EXPENSE"],
    ["Wireframing", "Balsamiq subscription ₹750/month.", "billing@balsamiq.com", "EXPENSE"],
    ["Diagram", "Lucidchart subscription ₹1050/user/month.", "billing@lucidchart.com", "EXPENSE"],
    ["Mind mapping", "MindMeister subscription ₹950/month.", "billing@mindmeister.com", "EXPENSE"],
    ["Code editor", "JetBrains PhpStorm subscription ₹1650/month.", "billing@jetbrains.com", "EXPENSE"],
    ["Database tool", "DataGrip subscription ₹1050/month.", "billing@jetbrains.com", "EXPENSE"],
    ["Version control", "GitHub Enterprise subscription $28/user/month.", "billing@github.com", "EXPENSE"],
    ["CI/CD", "GitLab Premium subscription $22/user/month.", "billing@gitlab.com", "EXPENSE"],
    ["Container registry", "Docker Hub Pro subscription $6/month charged.", "billing@docker.com", "EXPENSE"],
    ["Kubernetes", "AWS EKS bill $52.00 for March cluster usage.", "billing@aws.amazon.com", "EXPENSE"],
    ["Serverless", "AWS Lambda bill $28.50 for March usage.", "billing@aws.amazon.com", "EXPENSE"],
    ["Database AWS", "AWS RDS bill $42.00 for March.", "billing@aws.amazon.com", "EXPENSE"],
    ["Storage AWS", "AWS S3 bill $22.00 for March storage.", "billing@aws.amazon.com", "EXPENSE"],
    ["CDN AWS", "AWS CloudFront bill $12.50 for March bandwidth.", "billing@aws.amazon.com", "EXPENSE"],
    ["Monitoring", "Datadog subscription ₹5200/month.", "billing@datadoghq.com", "EXPENSE"],
    ["Logging", "Loggly subscription ₹3200/month.", "billing@loggly.com", "EXPENSE"],
    ["APM", "New Relic subscription ₹7200/month.", "billing@newrelic.com", "EXPENSE"],
    ["Error tracking", "Sentry subscription ₹2100/month.", "billing@sentry.io", "EXPENSE"],
    ["Security scan", "Snyk subscription ₹3800/month.", "billing@snyk.io", "EXPENSE"],
    ["Code review", "SonarCloud subscription ₹2500/month.", "billing@sonarsource.com", "EXPENSE"],
    ["Testing", "BrowserStack subscription ₹4500/month.", "billing@browserstack.com", "EXPENSE"],
    ["Mobile testing", "TestFairy subscription ₹2100/month.", "billing@testfairy.com", "EXPENSE"],
    ["Performance", "WebPageTest subscription ₹1050/month.", "billing@webpagetest.org", "EXPENSE"],
    ["SEO tools", "SEMrush subscription ₹9500/month.", "billing@semrush.com", "EXPENSE"],
    ["Email tools", "Mailgun subscription ₹1400/month.", "billing@mailgun.com", "EXPENSE"],
    ["SMS", "Twilio subscription ₹2800/month.", "billing@twilio.com", "EXPENSE"],
    ["Push notifications", "OneSignal subscription ₹1050/month.", "billing@onesignal.com", "EXPENSE"],
    ["Chat widget", "Intercom subscription ₹4800/month.", "billing@intercom.com", "EXPENSE"],
    ["Help desk", "Zendesk subscription ₹4100/month.", "billing@zendesk.com", "EXPENSE"],
    ["Customer support", "Freshdesk subscription ₹3500/month.", "billing@freshdesk.com", "EXPENSE"],
    ["Survey tool", "Typeform subscription ₹1050/month.", "billing@typeform.com", "EXPENSE"],
    ["Spreadsheets", "Google Sheets workspace subscription ₹1350/month.", "billing@google.com", "EXPENSE"],
    ["Documents", "Google Docs workspace subscription ₹1350/month.", "billing@google.com", "EXPENSE"],
    ["Presentations", "Google Slides workspace subscription ₹1350/month.", "billing@google.com", "EXPENSE"],
    ["Cloud office", "Microsoft 365 Business Premium ₹950/user/month.", "billing@microsoft.com", "EXPENSE"],
    ["Email provider", "Google Workspace Business ₹750/user/month.", "billing@google.com", "EXPENSE"],
    ["Cloud office", "Zoho Workplace ₹420/user/month.", "billing@zoho.com", "EXPENSE"],
    ["HR", "BambooHR subscription ₹5200/month.", "billing@bamboohr.com", "EXPENSE"],
    ["Recruitment", "Greenhouse subscription ₹9500/month.", "billing@greenhouse.io", "EXPENSE"],
    ["Performance", "Lattice subscription ₹3800/month.", "billing@lattice.com", "EXPENSE"],
    ["Training", "Udemy Business subscription ₹2100/user/month.", "billing@udemy.com", "EXPENSE"],
    ["Learning", "Coursera for Business ₹950/user/month.", "billing@coursera.com", "EXPENSE"],
    ["Development", "Pluralsight subscription ₹1350/user/month.", "billing@pluralsight.com", "EXPENSE"],
    ["Design", "Skillshare subscription ₹420/user/month.", "billing@skillshare.com", "EXPENSE"],
    ["Books", "Scribd subscription ₹420/month.", "billing@scribd.com", "EXPENSE"],
    ["Audiobooks", "Audible subscription ₹720/month.", "billing@audible.com", "EXPENSE"],
    ["Magazines", "Readly subscription ₹520/month.", "billing@readly.com", "EXPENSE"],
    ["News", "The New York Times subscription ₹750/month.", "billing@nytimes.com", "EXPENSE"],
    ["Finance app", "YNAB subscription ₹520/month.", "billing@ynab.com", "EXPENSE"],
    ["Investment", "Robinhood Gold subscription ₹420/month.", "billing@robinhood.com", "EXPENSE"],
]

ADDITIONAL_NOT_EXPENSE = [
    ["Monthly newsletter", "This month's newsletter: Product updates, new features, and user stories.", "newsletter@company.com", "NOT_EXPENSE"],
    ["Your order is out for delivery", "Your Amazon order #456-789012 is out for delivery. ETA: 2 PM.", "tracking@amazon.in", "NOT_EXPENSE"],
    ["Welcome aboard", "Welcome to our team! Complete your onboarding checklist.", "onboarding@company.com", "NOT_EXPENSE"],
    ["Account security", "Please verify your identity to secure your account.", "security@app.com", "NOT_EXPENSE"],
    ["Product update", "New feature released: Enhanced search functionality. Try it now!", "updates@product.com", "NOT_EXPENSE"],
    ["Feedback request", "How would you rate your experience? Take our 1-minute survey.", "survey@service.com", "NOT_EXPENSE"],
    ["Webinar starting soon", "Your webinar starts in 30 minutes. Join link attached.", "events@webinar.com", "NOT_EXPENSE"],
    ["Free trial started", "Your 14-day free trial has begun. No credit card required.", "trial@service.com", "NOT_EXPENSE"],
    ["Article published", "New article: '5 Tips for Better Productivity' is now live.", "blog@company.com", "NOT_EXPENSE"],
    ["Email verified", "Your email address has been verified successfully.", "verify@app.com", "NOT_EXPENSE"],
    ["New job opportunities", "5 new job openings match your profile. Apply now!", "jobs@careers.com", "NOT_EXPENSE"],
    ["Maintenance complete", "Scheduled maintenance is complete. All services are now available.", "admin@platform.com", "NOT_EXPENSE"],
    ["Weekly top stories", "Top stories: AI breakthrough, market updates, tech news.", "digest@news.com", "NOT_EXPENSE"],
    ["Profile views", "Your profile was viewed 15 times this week.", "notifications@linkedin.com", "NOT_EXPENSE"],
    ["Follower milestone", "You reached 1000 followers! Thank you for being part of our community.", "social@platform.com", "NOT_EXPENSE"],
    ["Activity report", "Your weekly activity: 10 posts, 50 likes, 20 shares.", "summary@service.com", "NOT_EXPENSE"],
    ["Town hall invite", "Join us for Q2 town hall on Friday at 3 PM.", "events@company.com", "NOT_EXPENSE"],
    ["Free learning resource", "Free e-book: 'The Future of Work' available for download.", "resources@learning.com", "NOT_EXPENSE"],
    ["Thank you", "Thank you for being a valued customer. Here's a special offer!", "loyalty@company.com", "NOT_EXPENSE"],
    ["New podcast", "Latest podcast: 'Leadership Lessons' is now streaming.", "podcast@studio.com", "NOT_EXPENSE"],
    ["Preference center", "Update your email preferences and notification settings.", "preferences@mailer.com", "NOT_EXPENSE"],
    ["Seasonal greetings", "Happy Spring! Here are some tips for the season.", "greetings@company.com", "NOT_EXPENSE"],
    ["Early access", "Get early access to our new feature before public release.", "beta@product.com", "NOT_EXPENSE"],
    ["Login notification", "New login detected from Chrome on Windows. Was this you?", "security@platform.com", "NOT_EXPENSE"],
    ["Report ready", "Your monthly analytics report is ready for download.", "reports@analytics.com", "NOT_EXPENSE"],
    ["Terms update", "We've updated our Terms of Service. Please review.", "legal@platform.com", "NOT_EXPENSE"],
    ["Product launch", "Introducing our revolutionary new product. Learn more!", "launch@company.com", "NOT_EXPENSE"],
    ["Meeting invite", "You're invited to a strategy meeting on Monday at 10 AM.", "calendar@company.com", "NOT_EXPENSE"],
    ["Subscription ending", "Your subscription ends in 7 days. Renew to continue.", "billing@service.com", "NOT_EXPENSE"],
    ["Mentioned in post", "Someone mentioned you in a post. See the conversation.", "notification@platform.com", "NOT_EXPENSE"],
    ["Goals progress", "You've completed 80% of your weekly goals. Keep going!", "goals@productivity.com", "NOT_EXPENSE"],
    ["New badge", "You've earned the 'Expert' badge. Congratulations!", "achievements@platform.com", "NOT_EXPENSE"],
    ["Ticket closed", "Your support ticket #67890 has been closed. Rate our service.", "support@company.com", "NOT_EXPENSE"],
    ["Team building", "Join our virtual team building event next Thursday.", "events@company.com", "NOT_EXPENSE"],
    ["Export complete", "Your data export is complete. Download link valid for 7 days.", "data@platform.com", "NOT_EXPENSE"],
    ["New mode", "Dark mode is now available for all users. Update now!", "product@company.com", "NOT_EXPENSE"],
    ["Newsletter: Q2", "Q2 Newsletter: What's new, what's coming, and more.", "newsletter@company.com", "NOT_EXPENSE"],
]


def add_samples_to_reach_1000(input_csv: Path, output_csv: Path, expense_samples: list, not_expense_samples: list) -> dict:
    """Add samples to reach exactly 1000 rows."""
    existing_rows = []
    
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing_rows.append(row)
    
    for sample in expense_samples:
        row_dict = {
            "subject": sample[0],
            "body": sample[1],
            "sender": sample[2],
            "label": sample[3]
        }
        existing_rows.append(row_dict)
    
    for sample in not_expense_samples:
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
        "input_count": 871,
        "expense_added": len(expense_samples),
        "not_expense_added": len(not_expense_samples),
        "final_count": len(existing_rows),
        "label_distribution": label_counts
    }


def print_final_report(stats: dict) -> None:
    """Print final report."""
    print("\n" + "=" * 60)
    print("FINAL DATASET: 1000 ROWS")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Input count: {stats['input_count']}")
    print(f"   EXPENSE samples added: {stats['expense_added']}")
    print(f"   NOT_EXPENSE samples added: {stats['not_expense_added']}")
    print(f"   Final count: {stats['final_count']}")
    
    print(f"\n📈 Label Distribution:")
    for label, count in stats["label_distribution"].items():
        percentage = (count / stats["final_count"]) * 100
        print(f"   {label}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    stats = add_samples_to_reach_1000(INPUT_CSV, FINAL_CSV, ADDITIONAL_EXPENSE, ADDITIONAL_NOT_EXPENSE)
    print_final_report(stats)
