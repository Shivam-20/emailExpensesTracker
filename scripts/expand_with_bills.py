#!/usr/bin/env python3

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
TRAINING_CSV = DATA_DIR / "training_emails.csv"
EXPANDED_CSV = DATA_DIR / "training_emails_expanded.csv"

CREDIT_CARD_BILL_SAMPLES = [
    ["Credit card bill generated", "Your HDFC credit card bill for the period Feb 15 - Mar 15 has been generated. Total due: ₹24500. Payment due: March 25.", "statements@hdfcbank.com", "EXPENSE"],
    ["Credit card statement ready", "Your ICICI Bank credit card statement for March is now available. Login to net banking to view.", "statements@icicibank.com", "EXPENSE"],
    ["New credit card bill", "Your Kotak811 credit card bill for March is ready. Total outstanding: ₹18900. Minimum due: ₹1890.", "bills@kotak.com", "EXPENSE"],
    ["Card bill notification", "Your SBI credit card ending 4567 has a bill of ₹32450 due on April 10. Minimum due: ₹3245.", "cards@sbi.co.in", "EXPENSE"],
    ["Credit card payment reminder", "Payment reminder: Your Axis Bank credit card bill of ₹15600 is due on March 28. Pay now to avoid late fees.", "reminders@axisbank.com", "EXPENSE"],
    ["Bill generation alert", "Your Citi credit card statement for period March 1-31 is generated. Total charges: ₹28900.", "citicards@citi.com", "EXPENSE"],
    ["Credit card dues", "Your American Express card payment of ₹42000 is due on April 5. Minimum amount due: ₹2100.", "payments@americanexpress.com", "EXPENSE"],
    ["Monthly card statement", "Your HSBC credit card monthly statement is ready. Total spent: ₹19500. Due date: April 8.", "statements@hsbc.co.in", "EXPENSE"],
    ["Card bill summary", "Your Standard Chartered credit card bill for March: ₹22150. Payment due: March 30.", "cards@sc.com", "EXPENSE"],
    ["Credit card period bill", "Your Yes Bank credit card statement for billing period Feb 20 - Mar 19 is now available. Total: ₹17350.", "yescreditcards@yesbank.in", "EXPENSE"],
    ["New bill notification", "Your RBL Bank credit card bill of ₹14500 has been generated. Minimum due: ₹1450. Due: March 31.", "bills@rblbank.com", "EXPENSE"],
    ["Credit card outstanding", "Your IndusInd Bank credit card outstanding amount: ₹26700. Last date to pay: April 12.", "cards@indusind.com", "EXPENSE"],
    ["Bill due reminder", "Payment reminder for your Bank of Baroda credit card: ₹19800 due on April 3. Avoid late payment charges.", "reminders@bankofbaroda.com", "EXPENSE"],
    ["Card statement available", "Your Canara Bank credit card statement for March is now available. Total due: ₹21200.", "statements@canarabank.in", "EXPENSE"],
    ["Credit card bill summary", "Your PNB credit card bill summary: Charges ₹18950, Credits ₹2500, Net payable ₹16450. Due: April 7.", "bills@pnb.co.in", "EXPENSE"],
    ["Monthly bill alert", "Your Union Bank credit card monthly bill of ₹23400 is generated. Pay by April 15 to avoid interest.", "alerts@unionbankofindia.com", "EXPENSE"],
    ["Statement period ended", "Your IDFC First credit card statement period Mar 1-31 ended. Total dues: ₹17800. Minimum due: ₹1780.", "statements@idfc.com", "EXPENSE"],
    ["Credit card dues notification", "Your AU Small Finance Bank credit card dues: ₹14200. Payment due: March 29. Minimum due: ₹1420.", "reminders@aubank.com", "EXPENSE"],
    ["New credit card statement", "Your Federal Bank credit card statement for March is ready. Total outstanding: ₹20600. Due: April 10.", "cards@federalbank.co.in", "EXPENSE"],
    ["Bill generated: HDFC", "HDFC credit card bill generated for card ending 5678. Total: ₹28900. Pay by April 5.", "billing@hdfcbank.com", "EXPENSE"],
    ["Credit card payment due", "Your ICICI credit card payment of ₹34500 is due on April 12. Minimum due: ₹3450.", "payments@icicibank.com", "EXPENSE"],
    ["Kotak card bill", "Kotak811 credit card statement for March: ₹22300. Total amount due. Minimum: ₹2230.", "statements@kotak.com", "EXPENSE"],
    ["SBI card dues", "SBI credit card dues for card ending 8901: ₹38900. Due date: April 15. Minimum due: ₹3890.", "cards@sbi.co.in", "EXPENSE"],
    ["Axis card bill", "Axis Bank credit card bill for March: ₹24500. Payment due: April 8. Avoid late fees.", "bills@axisbank.com", "EXPENSE"],
    ["Citi card statement", "Citi credit card statement ready. Total charges: ₹31200. Payment due: April 10.", "citicards@citi.com", "EXPENSE"],
    ["Amex bill notification", "American Express card bill: ₹45000. Minimum due: ₹2250. Payment date: April 20.", "billing@americanexpress.com", "EXPENSE"],
    ["HSBC card bill", "HSBC credit card statement: ₹19800. Due on April 12. Minimum amount: ₹1980.", "statements@hsbc.co.in", "EXPENSE"],
    ["Standard Chartered bill", "Standard Chartered credit card bill: ₹26500. Payment due: April 5.", "cards@sc.com", "EXPENSE"],
    ["Yes Bank card dues", "Yes Bank credit card outstanding: ₹18900. Last date to pay: April 18.", "yescreditcards@yesbank.in", "EXPENSE"],
    ["RBL card bill", "RBL Bank credit card bill generated: ₹15600. Minimum due: ₹1560. Due: April 8.", "bills@rblbank.com", "EXPENSE"],
    ["IndusInd card dues", "IndusInd Bank credit card payment due: ₹24300. Due date: April 3.", "cards@indusind.com", "EXPENSE"],
    ["BOB card reminder", "Bank of Baroda credit card: ₹21500 due on April 10. Pay now.", "reminders@bankofbaroda.com", "EXPENSE"],
    ["Canara card statement", "Canara Bank credit card bill: ₹23400. Due on April 15.", "statements@canarabank.in", "EXPENSE"],
    ["PNB card bill", "PNB credit card statement: ₹19200. Minimum due: ₹1920. Due: April 12.", "bills@pnb.co.in", "EXPENSE"],
    ["Union Bank card bill", "Union Bank credit card: ₹25600. Pay by April 20 to avoid interest.", "alerts@unionbankofindia.com", "EXPENSE"],
    ["IDFC card statement", "IDFC First credit card: ₹16500. Minimum due: ₹1650. Due: April 5.", "statements@idfc.com", "EXPENSE"],
    ["AU Bank card dues", "AU Small Finance Bank credit card: ₹13400. Due: March 31. Minimum: ₹1340.", "reminders@aubank.com", "EXPENSE"],
    ["Federal Bank card bill", "Federal Bank credit card: ₹22300. Due on April 18.", "cards@federalbank.co.in", "EXPENSE"],
    ["HDFC card payment reminder", "Payment reminder: HDFC credit card bill ₹29800 due on April 8. Minimum due: ₹2980.", "reminders@hdfcbank.com", "EXPENSE"],
    ["ICICI card summary", "ICICI credit card bill summary: ₹35600. Charges ₹38900, Credits ₹3300. Due: April 15.", "billing@icicibank.com", "EXPENSE"],
    ["Kotak card dues", "Kotak811 credit card dues: ₹23400. Last date: April 10. Minimum: ₹2340.", "yescreditcards@yesbank.in", "EXPENSE"],
    ["SBI card statement", "SBI credit card statement for March: ₹40200. Total outstanding. Due: April 20.", "statements@sbi.co.in", "EXPENSE"],
    ["Axis card payment due", "Axis Bank credit card: ₹25800 due on April 12. Minimum due: ₹2580.", "payments@axisbank.com", "EXPENSE"],
    ["Citi card payment", "Citi credit card payment due: ₹32500. Pay by April 15 to avoid late fees.", "citicards@citi.com", "EXPENSE"],
    ["Amex card statement", "American Express card statement: ₹47500. Minimum due: ₹2375. Due: April 25.", "statements@americanexpress.com", "EXPENSE"],
    ["HSBC card dues", "HSBC credit card dues: ₹20800. Payment due: April 18.", "cards@hsbc.co.in", "EXPENSE"],
    ["Standard Chartered payment", "Standard Chartered credit card: ₹27800. Due on April 8.", "payments@sc.com", "EXPENSE"],
    ["Yes Bank card bill", "Yes Bank credit card bill: ₹19800. Last date: April 20. Minimum: ₹1980.", "bills@yesbank.in", "EXPENSE"],
    ["RBL card statement", "RBL Bank credit card statement: ₹16700. Minimum due: ₹1670. Due: April 12.", "statements@rblbank.com", "EXPENSE"],
    ["IndusInd card bill", "IndusInd Bank credit card: ₹25600. Due date: April 5.", "bills@indusind.com", "EXPENSE"],
    ["BOB card dues", "Bank of Baroda credit card: ₹22800 due on April 15. Pay now.", "cards@bankofbaroda.com", "EXPENSE"],
    ["Canara card payment", "Canara Bank credit card: ₹24500 due on April 20. Minimum due: ₹2450.", "payments@canarabank.in", "EXPENSE"],
    ["PNB card dues", "PNB credit card dues: ₹20300. Due: April 18. Minimum: ₹2030.", "cards@pnb.co.in", "EXPENSE"],
    ["Union Bank card", "Union Bank credit card: ₹26800. Pay by April 25 to avoid interest.", "bills@unionbankofindia.com", "EXPENSE"],
    ["IDFC card bill", "IDFC First credit card: ₹17600. Minimum due: ₹1760. Due: April 8.", "cards@idfc.com", "EXPENSE"],
    ["AU Bank card", "AU Small Finance Bank credit card: ₹14500. Due: April 5. Minimum: ₹1450.", "cards@aubank.com", "EXPENSE"],
    ["Federal Bank dues", "Federal Bank credit card: ₹23400. Due on April 20.", "bills@federalbank.co.in", "EXPENSE"],
]

BILL_STATEMENT_SAMPLES = [
    ["Electricity bill generated", "Your BSES electricity bill for March is generated. Amount: ₹2450. Due date: April 10.", "bills@bsesdelhi.com", "EXPENSE"],
    ["Water bill ready", "Delhi Jal Board water bill of ₹425 is ready. Consumer no: 987654321. Due: April 5.", "payments@djb.gov.in", "EXPENSE"],
    ["Gas bill statement", "Mahanagar Gas bill for March: ₹920. Due: April 8. Pay now to avoid disconnection.", "billing@mahanagargas.com", "EXPENSE"],
    ["Phone bill generated", "Airtel postpaid bill for March: ₹799. Due: April 12. Auto-pay enabled.", "billing@airtel.in", "EXPENSE"],
    ["Mobile bill", "Jio postpaid bill: ₹599 for March. Due: April 8. Payment received via autopay.", "recharge@jio.com", "EXPENSE"],
    ["DTH bill ready", "Tata Play DTH bill for March: ₹450. Due: April 10. Pack: Hindi Smart HD.", "billing@tataplay.com", "EXPENSE"],
    ["Broadband bill", "BSNL broadband bill: ₹899 for March. Due: April 15.", "payments@bsnl.co.in", "EXPENSE"],
    ["Internet bill", "ACT Fibernet bill for March: ₹1299. Due: April 12. Auto-pay active.", "billing@actcorp.in", "EXPENSE"],
    ["Landline bill", "MTNL landline bill for March: ₹550. Due: April 18.", "billing@mtel.in", "EXPENSE"],
    ["Gas cylinder bill", "Indane LPG cylinder booking payment: ₹903. Booking ID: HP987654321.", "noreply@indianoil.in", "EXPENSE"],
    ["Property tax bill", "Municipal property tax for FY 2026-27: ₹12500. Due: March 31. Pay online.", "receipts@mcgm.gov.in", "EXPENSE"],
    ["Water tax", "Annual water tax payment: ₹3500. Due: April 15. Pay through municipal portal.", "taxes@corporation.gov.in", "EXPENSE"],
    ["Power bill", "MSEDCL electricity bill: ₹2890 for March. Consumer: 1234567. Due: April 20.", "payments@mahadiscom.in", "EXPENSE"],
    ["Energy bill", "TNEB electricity bill: ₹1850. Due: April 10. Pay now.", "eb@tneb.tn.gov.in", "EXPENSE"],
    ["Electricity statement", "KSEB electricity bill for March: ₹2200. Due: April 8.", "kseb@kerala.gov.in", "EXPENSE"],
    ["Power bill ready", "AP electricity bill: ₹2650 for March. Consumer: 987654. Due: April 15.", "apspdcl@ap.gov.in", "EXPENSE"],
    ["Metro water bill", "Chennai Metro Water bill: ₹520. Due: April 5. Consumer: CMW123456.", "payments@cmwssb.tn.gov.in", "EXPENSE"],
    ["Sewerage bill", "Annual sewerage tax: ₹2800. Due: March 31. Pay online.", "taxes@municipal.gov.in", "EXPENSE"],
    ["Solid waste bill", "Waste management bill: ₹1200 for Q1. Due: April 10.", "sanitation@corporation.gov.in", "EXPENSE"],
    ["Street light tax", "Annual street light tax: ₹450. Due: March 31.", "taxes@municipality.gov.in", "EXPENSE"],
]

LOAN_EMI_SAMPLES = [
    ["Home loan EMI deducted", "Your HDFC home loan EMI of ₹35000 has been auto-debited from your account. Loan: HL-2024-789.", "emi@hdfc.com", "EXPENSE"],
    ["Personal loan EMI", "Axis Bank personal loan EMI ₹18500 deducted for March. Loan: PL-2023-456.", "emi@axisbank.com", "EXPENSE"],
    ["Car loan EMI", "ICICI Bank car loan EMI ₹22500 auto-debited. Loan: CL-2024-123.", "loans@icicibank.com", "EXPENSE"],
    ["Education loan EMI", "SBI education loan EMI ₹12000 deducted. Loan: ED-2022-789.", "emi@sbi.co.in", "EXPENSE"],
    ["Two-wheeler loan EMI", "Kotak two-wheeler loan EMI ₹3500 paid. Loan: TW-2024-234.", "emi@kotak.com", "EXPENSE"],
    ["Gold loan EMI", "Muthoot Finance gold loan EMI ₹4500 paid. Loan: GL-2024-567.", "emi@muthoot.com", "EXPENSE"],
    ["Personal finance EMI", "Bajaj Finserv personal loan EMI ₹9500 deducted. Loan: PFL-2024-890.", "emi@bajajfinserv.in", "EXPENSE"],
    ["Consumer loan EMI", "HDFC consumer durable loan EMI ₹2800 deducted. Loan: CD-2024-345.", "emi@hdfc.com", "EXPENSE"],
    ["Business loan EMI", "ICICI Bank business loan EMI ₹45000 paid. Loan: BL-2024-678.", "loans@icicibank.com", "EXPENSE"],
    ["Mortgage EMI", "LIC home loan EMI ₹42000 auto-debited. Loan: HL-2020-123.", "emi@licindia.in", "EXPENSE"],
    ["Loan EMI reminder", "Payment reminder: Your personal loan EMI of ₹19500 is due on April 5. Pay now.", "reminders@bank.com", "EXPENSE"],
    ["EMI payment successful", "Your car loan EMI of ₹23000 has been paid successfully. Loan: CL-2024-123.", "payments@bank.com", "EXPENSE"],
    ["Loan EMI alert", "Education loan EMI ₹12500 debited from account. Loan: ED-2022-789.", "alerts@bank.com", "EXPENSE"],
    ["Pre-EMI interest", "Home loan pre-EMI interest of ₹2500 charged. Account: HL-2024-789.", "interest@hdfc.com", "EXPENSE"],
    ["Loan installment due", "Two-wheeler loan installment ₹3800 due on April 10. Loan: TW-2024-234.", "installment@kotak.com", "EXPENSE"],
    ["Gold loan interest", "Gold loan interest ₹850 debited. Loan: GL-2024-567.", "interest@muthoot.com", "EXPENSE"],
    ["Business loan payment", "Business loan EMI ₹47000 paid. Loan: BL-2024-678.", "business@icicibank.com", "EXPENSE"],
    ["Consumer durable EMI", "Consumer loan EMI ₹2900 paid for refrigerator. Loan: CD-2024-345.", "consumer@hdfc.com", "EXPENSE"],
    ["Personal loan due", "Personal loan installment ₹20500 due on April 8. Loan: PFL-2024-890.", "due@bajajfinserv.in", "EXPENSE"],
    ["Mortgage payment", "Mortgage payment ₹43500 processed. Loan: HL-2020-123.", "payment@licindia.in", "EXPENSE"],
]

INSURANCE_PREMIUM_SAMPLES = [
    ["Health insurance premium", "Star Health insurance premium of ₹12500 is due on April 5. Policy: HL-2024-789.", "premium@starhealth.in", "EXPENSE"],
    ["Car insurance renewal", "ICICI Lombard car insurance policy renewed. Premium: ₹14500. Policy: CL-2024-456.", "renewal@icicilombard.com", "EXPENSE"],
    ["Life insurance premium", "LIC term insurance premium of ₹18500 auto-debited. Policy: LI-2024-123.", "premium@licindia.in", "EXPENSE"],
    ["Two-wheeler insurance", "HDFC Ergo two-wheeler insurance ₹3800 paid. Policy: TW-2024-678.", "insurance@hdfcergo.com", "EXPENSE"],
    ["Travel insurance", "Reliance Travel insurance purchased. Premium: ₹850. Policy: TL-2024-234.", "buy@reliancegeneral.co.in", "EXPENSE"],
    ["Home insurance", "Bajaj Allianz home insurance premium ₹6500 due on April 10. Policy: HI-2024-567.", "premium@bajajallianz.com", "EXPENSE"],
    ["Critical illness insurance", "Aditya Birla critical illness insurance premium ₹4200 deducted. Policy: CI-2024-890.", "premium@adityabirlahealth.com", "EXPENSE"],
    ["Personal accident insurance", "National Insurance personal accident policy ₹1200 renewed. Policy: PA-2024-345.", "renewal@nationalinsurance.co.in", "EXPENSE"],
    ["Medical insurance", "Max Bupa health insurance premium ₹15000 due on April 15. Policy: MB-2024-678.", "premium@maxbupa.com", "EXPENSE"],
    ["Vehicle insurance", "United India vehicle insurance ₹6800 paid. Policy: VL-2024-901.", "insurance@uiic.co.in", "EXPENSE"],
    ["Term life insurance", "HDFC Life term insurance premium ₹22000 auto-debited. Policy: TL-2024-234.", "premium@hdfclife.com", "EXPENSE"],
    ["Family health insurance", "Apollo Munich family floater premium ₹25000 due. Policy: FH-2024-567.", "premium@apollomunich.com", "EXPENSE"],
    ["Motor insurance", "IFFCO-Tokio motor insurance premium ₹5200 paid. Policy: MI-2024-890.", "insurance@iffcotokio.co.in", "EXPENSE"],
    ["Group health insurance", "ICICI Pru group health premium ₹18500 deducted. Policy: GH-2024-123.", "premium@icicipru.com", "EXPENSE"],
    ["Accident insurance", "Bharti AXA personal accident policy ₹950 renewed. Policy: PA-2024-456.", "renewal@bhartiaxa.com", "EXPENSE"],
    ["Householders insurance", "Oriental Insurance householders policy ₹3200 due. Policy: HH-2024-789.", "premium@orientalinsurance.co.in", "EXPENSE"],
    ["Medical insurance premium", "Care Health insurance premium ₹13500 auto-debited. Policy: CH-2024-234.", "premium@carehealth.com", "EXPENSE"],
    ["Comprehensive vehicle insurance", "Royal Sundaram comprehensive insurance ₹7500 paid. Policy: CV-2024-567.", "insurance@royalsundaram.in", "EXPENSE"],
    ["Critical care insurance", "Manipal Cigna critical care premium ₹4500 deducted. Policy: CC-2024-890.", "premium@manpalcigna.com", "EXPENSE"],
    ["Life insurance due", "SBI Life insurance premium ₹19500 due on April 20. Policy: SL-2024-123.", "due@sbilife.co.in", "EXPENSE"],
]

SUBSCRIPTION_SAMPLES = [
    ["Netflix subscription renewed", "Your Netflix Premium subscription has been renewed. ₹649 charged to HDFC card 4567. Valid until May 2026.", "no-reply@netflix.com", "EXPENSE"],
    ["Amazon Prime renewal", "Amazon Prime annual membership renewed. ₹1499 charged to ICICI card. Valid until March 2027.", "prime@amazon.in", "EXPENSE"],
    ["Spotify Premium", "Spotify Premium subscription ₹119/month charged to card. Renewal date: April 2026.", "no-reply@spotify.com", "EXPENSE"],
    ["YouTube Premium", "YouTube Music + Premium ₹129 charged to UPI. Subscription active until May 2026.", "billing@youtube.com", "EXPENSE"],
    ["Apple Music", "Apple Music subscription ₹99 charged to Apple Pay. Renewed until April 2026.", "no-reply@email.apple.com", "EXPENSE"],
    ["Zomato Gold", "Zomato Gold membership renewed for 3 months. ₹450 charged to card.", "membership@zomato.com", "EXPENSE"],
    ["Swiggy One", "Swiggy One membership renewed. ₹199 for 1 month. Free deliveries activated.", "membership@swiggy.com", "EXPENSE"],
    ["Audible subscription", "Audible audiobook subscription ₹749 charged to card. Monthly plan renewed.", "noreply@audible.com", "EXPENSE"],
    ["Kindle Unlimited", "Kindle Unlimited subscription ₹169 charged to Amazon Pay. Monthly plan active.", "kindle@amazon.com", "EXPENSE"],
    ["Google One", "Google One 200GB storage plan ₹130 charged to GPay. Storage upgraded.", "payments-noreply@google.com", "EXPENSE"],
    ["iCloud storage", "iCloud+ 200GB plan ₹75 charged to card. Storage renewed until May 2026.", "no-reply@email.apple.com", "EXPENSE"],
    ["Dropbox Plus", "Dropbox Plus 2TB subscription ₹950 charged to card. Monthly plan renewed.", "billing@dropbox.com", "EXPENSE"],
    ["OneDrive storage", "Microsoft OneDrive 100GB ₹195 charged. Storage plan renewed.", "billing@microsoft.com", "EXPENSE"],
    ["Canva Pro", "Canva Pro subscription ₹599 charged to card. Monthly plan active.", "billing@canva.com", "EXPENSE"],
    ["Adobe Creative Cloud", "Adobe Creative Cloud All Apps ₹2200 charged. Monthly plan renewed.", "billing@adobe.com", "EXPENSE"],
    ["Microsoft 365", "Microsoft 365 Family ₹5299 charged. Annual subscription renewed.", "billing@microsoft.com", "EXPENSE"],
    ["Slack Pro", "Slack Pro subscription ₹880 per user charged. Monthly plan active.", "billing@slack.com", "EXPENSE"],
    ["Zoom Pro", "Zoom Pro subscription ₹1350 charged. Monthly plan renewed.", "billing@zoom.us", "EXPENSE"],
    ["Notion Personal", "Notion Personal Pro ₹429 charged. Monthly plan active.", "billing@notion.so", "EXPENSE"],
    ["Figma Professional", "Figma Professional ₹1200 charged. Monthly plan renewed.", "billing@figma.com", "EXPENSE"],
    ["Asana Premium", "Asana Premium ₹450 per user charged. Monthly plan active.", "billing@asana.com", "EXPENSE"],
    ["Trello Gold", "Trello Gold subscription ₹350 charged. Annual plan renewed.", "billing@trello.com", "EXPENSE"],
    ["Evernote Personal", "Evernote Personal ₹449 charged. Monthly plan renewed.", "billing@evernote.com", "EXPENSE"],
    ["1Password", "1Password Families subscription ₹280 charged. Monthly plan active.", "billing@1password.com", "EXPENSE"],
    ["NordVPN", "NordVPN subscription ₹950 charged. Annual plan renewed.", "billing@nordvpn.com", "EXPENSE"],
    ["ExpressVPN", "ExpressVPN subscription ₹1050 charged. Annual plan active.", "billing@expressvpn.com", "EXPENSE"],
    ["Surfshark", "Surfshark VPN subscription ₹650 charged. Annual plan renewed.", "billing@surfshark.com", "EXPENSE"],
    ["Grammarly Premium", "Grammarly Premium ₹990 charged. Annual plan renewed.", "billing@grammarly.com", "EXPENSE"],
    ["Hootsuite", "Hootsuite Professional ₹3200 charged. Monthly plan active.", "billing@hootsuite.com", "EXPENSE"],
    ["Buffer", "Buffer Pro subscription ₹950 charged. Monthly plan renewed.", "billing@buffer.com", "EXPENSE"],
    ["Sprout Social", "Sprout Social subscription ₹8500 charged. Monthly plan active.", "billing@sproutsocial.com", "EXPENSE"],
    ["Ahrefs", "Ahrefs Lite subscription ₹8500 charged. Monthly plan renewed.", "billing@ahrefs.com", "EXPENSE"],
    ["SEMrush", "SEMrush Guru subscription ₹9500 charged. Monthly plan active.", "billing@semrush.com", "EXPENSE"],
    ["Moz Pro", "Moz Pro subscription ₹6500 charged. Monthly plan renewed.", "billing@moz.com", "EXPENSE"],
    ["Udemy", "Udemy course 'Machine Learning A-Z' ₹1299 purchased. Lifetime access.", "noreply@udemy.com", "EXPENSE"],
    ["Coursera Plus", "Coursera Plus subscription ₹3500 charged. Annual plan active.", "billing@coursera.com", "EXPENSE"],
    ["Pluralsight", "Pluralsight subscription ₹1650 charged. Monthly plan renewed.", "billing@pluralsight.com", "EXPENSE"],
    ["Skillshare", "Skillshare subscription ₹420 charged. Annual plan active.", "billing@skillshare.com", "EXPENSE"],
    ["LinkedIn Premium", "LinkedIn Premium ₹1800 charged. Monthly plan renewed.", "billing@linkedin.com", "EXPENSE"],
    ["Indeed Premium", "Indeed Premium ₹1500 charged. Annual plan active.", "billing@indeed.com", "EXPENSE"],
    ["Glassdoor", "Glassdoor subscription ₹800 charged. Annual plan renewed.", "billing@glassdoor.com", "EXPENSE"],
    ["Medium membership", "Medium membership ₹350 charged. Monthly plan active.", "membership@medium.com", "EXPENSE"],
    ["Substack", "Substack newsletter subscription ₹350 charged. Monthly plan renewed.", "noreply@substack.com", "EXPENSE"],
    ["The Hindu", "The Hindu digital subscription ₹999 charged. Annual plan active.", "subscription@thehindu.com", "EXPENSE"],
    ["Times of India", "Times of India digital subscription ₹749 charged. Annual plan renewed.", "subscription@timesofindia.com", "EXPENSE"],
    ["Indian Express", "Indian Express digital subscription ₹699 charged. Annual plan active.", "subscription@indianexpress.com", "EXPENSE"],
    ["Scribd", "Scribd subscription ₹420 charged. Monthly plan renewed.", "billing@scribd.com", "EXPENSE"],
    ["Readly", "Readly magazine subscription ₹520 charged. Monthly plan active.", "billing@readly.com", "EXPENSE"],
    ["NYTimes", "New York Times digital subscription ₹750 charged. Monthly plan renewed.", "billing@nytimes.com", "EXPENSE"],
    ["The Economist", "The Economist subscription ₹850 charged. Annual plan active.", "subscription@economist.com", "EXPENSE"],
    ["Wall Street Journal", "WSJ digital subscription ₹950 charged. Monthly plan renewed.", "subscription@wsj.com", "EXPENSE"],
    ["Forbes", "Forbes digital subscription ₹650 charged. Annual plan active.", "subscription@forbes.com", "EXPENSE"],
    ["Business Insider", "Business Insider Premium ₹550 charged. Monthly plan renewed.", "premium@businessinsider.com", "EXPENSE"],
    ["HBR", "Harvard Business Review subscription ₹1200 charged. Annual plan active.", "subscription@hbr.org", "EXPENSE"],
    ["McKinsey Quarterly", "McKinsey Quarterly subscription ₹1800 charged. Annual plan renewed.", "subscription@mckinsey.com", "EXPENSE"],
    ["Deloitte Insights", "Deloitte Insights subscription ₹850 charged. Annual plan active.", "subscription@deloitte.com", "EXPENSE"],
    ["BCG Perspectives", "BCG Perspectives subscription ₹950 charged. Annual plan renewed.", "subscription@bcg.com", "EXPENSE"],
]

NOT_EXPENSE_NOTIFICATIONS = [
    ["Salary credit notification", "Your salary for March 2026 has been credited to your bank account. Net amount: ₹85000.", "payroll@company.com", "NOT_EXPENSE"],
    ["Dividend credited", "Dividend of ₹2500 has been credited to your account. Source: HDFC Equity Fund.", "dividend@bank.com", "NOT_EXPENSE"],
    ["Interest credited", "Quarterly interest of ₹1850 credited to your savings account.", "interest@bank.com", "NOT_EXPENSE"],
    ["Refund initiated", "Your refund of ₹950 has been initiated. Amount will reflect in 5-7 business days.", "refunds@company.com", "NOT_EXPENSE"],
    ["Cashback received", "₹200 PhonePe cashback credited for your recent Amazon purchase.", "rewards@phonepe.com", "NOT_EXPENSE"],
    ["Reward points earned", "You earned 500 reward points for your recent transaction. Points value: ₹500.", "rewards@bank.com", "NOT_EXPENSE"],
    ["Credit to account", "Credit of ₹5000 received from ABC Company Pvt Ltd via NEFT.", "credits@bank.com", "NOT_EXPENSE"],
    ["Income credited", "Freelance income of ₹15000 credited to your account. Ref: TXN20260325.", "income@upwork.com", "NOT_EXPENSE"],
    ["Investment return", "SIP return of ₹3500 credited from mutual fund. Fund: HDFC Equity.", "sip@bank.com", "NOT_EXPENSE"],
    ["Tax refund", "Income tax refund of ₹5500 initiated. Will credit to account in 7 days.", "refund@incometax.gov.in", "NOT_EXPENSE"],
    ["Payment received", "Payment of ₹25000 received for services rendered. Invoice: INV-2024-789.", "payments@company.com", "NOT_EXPENSE"],
    ["Royalty credited", "Royalty payment of ₹1200 credited to your account. Source: Creative Work.", "royalty@company.com", "NOT_EXPENSE"],
    ["Bonus credited", "Performance bonus of ₹25000 credited to your account. FY 2025-26.", "hr@company.com", "NOT_EXPENSE"],
    ["Commission received", "Sales commission of ₹8500 credited. Period: March 2026.", "commission@company.com", "NOT_EXPENSE"],
    ["Payout received", "Affiliate payout of ₹4200 received from partner program.", "payout@affiliate.com", "NOT_EXPENSE"],
    ["Credit alert", "Credit of ₹10000 received via IMPS from Ravi Kumar.", "alerts@bank.com", "NOT_EXPENSE"],
    ["Refund processed", "Your refund request of ₹780 has been processed. Amount credited to wallet.", "refunds@service.com", "NOT_EXPENSE"],
    ["Cashback awarded", "₹150 Amazon Pay cashback awarded for your recent purchase.", "rewards@amazon.in", "NOT_EXPENSE"],
    ["Points redeemed", "You redeemed 1000 reward points for ₹1000 discount.", "rewards@loyalty.com", "NOT_EXPENSE"],
    ["Welcome bonus", "Welcome bonus of ₹500 credited to your account. Start spending now!", "welcome@bank.com", "NOT_EXPENSE"],
    ["Referral bonus", "Referral bonus of ₹750 credited. Your friend signed up using your code.", "rewards@referral.com", "NOT_EXPENSE"],
    ["Birthday bonus", "Special birthday bonus of ₹200 credited to your account. Enjoy!", "bonuses@bank.com", "NOT_EXPENSE"],
    ["Anniversary bonus", "Account anniversary bonus: ₹300 credited for 3 years with us!", "anniversary@bank.com", "NOT_EXPENSE"],
    ["Festive bonus", "Festive season bonus of ₹1000 credited. Happy Holi!", "bonuses@bank.com", "NOT_EXPENSE"],
    ["Promotional credit", "Promotional credit of ₹500 added to your account. Valid for 30 days.", "promo@bank.com", "NOT_EXPENSE"],
    ["Cashback milestone", "Milestone cashback: ₹250 for spending ₹10000 this month.", "milestone@bank.com", "NOT_EXPENSE"],
    ["Reward redemption", "You redeemed reward points for ₹800 gift card. Points deducted: 800.", "rewards@loyalty.com", "NOT_EXPENSE"],
    ["Partner cashback", "Partner cashback of ₹180 from Flipkart purchase credited.", "partner@bank.com", "NOT_EXPENSE"],
    ["Shopping rewards", "Shopping rewards: ₹350 credited for purchases at partner stores.", "shopping@rewards.com", "NOT_EXPENSE"],
    ["Fuel rewards", "Fuel reward points: 450 points added. Value: ₹450.", "fuel@rewards.com", "NOT_EXPENSE"],
    ["Dining rewards", "Dining reward points: 300 points added for restaurant bills.", "dining@rewards.com", "NOT_EXPENSE"],
    ["Travel rewards", "Travel reward points: 800 points added for flight booking.", "travel@rewards.com", "NOT_EXPENSE"],
    ["Movie rewards", "Movie reward points: 250 points added for ticket purchases.", "movies@rewards.com", "NOT_EXPENSE"],
    ["Grocery rewards", "Grocery reward points: 400 points added for supermarket purchases.", "grocery@rewards.com", "NOT_EXPENSE"],
    ["Bill payment rewards", "Bill payment reward points: 350 points for utility bill payments.", "bills@rewards.com", "NOT_EXPENSE"],
    ["EMI reward", "EMI reward points: 500 points for successful EMI payments.", "emi@rewards.com", "NOT_EXPENSE"],
    ["Credit score reward", "Credit score reward: ₹100 for maintaining score above 750.", "creditscore@bank.com", "NOT_EXPENSE"],
    ["Loyalty bonus", "Loyalty bonus: ₹200 for being a premium member.", "loyalty@bank.com", "NOT_EXPENSE"],
    ["VIP bonus", "VIP bonus: ₹500 for achieving VIP status this month.", "vip@bank.com", "NOT_EXPENSE"],
    ["Exclusive offer credit", "Exclusive offer: ₹300 credit for completing this week's challenge.", "exclusive@bank.com", "NOT_EXPENSE"],
    ["Game reward", "Game reward: ₹150 for playing spin-to-win game.", "games@bank.com", "NOT_EXPENSE"],
    ["Quiz reward", "Quiz reward: ₹100 for answering daily quiz correctly.", "quiz@bank.com", "NOT_EXPENSE"],
    ["Survey reward", "Survey reward: ₹200 for completing customer satisfaction survey.", "survey@bank.com", "NOT_EXPENSE"],
    ["App review reward", "App review reward: ₹50 for rating our app 5 stars.", "review@bank.com", "NOT_EXPENSE"],
    ["Invite friends reward", "Invite friends reward: ₹1000 for inviting 5 friends to the app.", "invite@bank.com", "NOT_EXPENSE"],
    ["Spending milestone", "Spending milestone reward: ₹500 for reaching ₹50000 spend this month.", "spending@bank.com", "NOT_EXPENSE"],
    ["Bill pay reward", "Bill pay reward: ₹150 for paying 3 bills this month.", "billpay@bank.com", "NOT_EXPENSE"],
    ["UPI transaction reward", "UPI transaction reward: ₹50 for 10 UPI transactions this month.", "upi@bank.com", "NOT_EXPENSE"],
    ["Card swipe reward", "Card swipe reward: ₹200 for 20 card swipes this month.", "card@bank.com", "NOT_EXPENSE"],
    ["Merchant offer reward", "Merchant offer reward: ₹150 for spending ₹2000 at partner merchant.", "merchant@bank.com", "NOT_EXPENSE"],
    ["Category spend reward", "Category spend reward: ₹300 for spending ₹5000 on groceries.", "category@bank.com", "NOT_EXPENSE"],
    ["Time-based reward", "Time-based reward: ₹100 for first transaction of the day.", "time@bank.com", "NOT_EXPENSE"],
    ["Weekend reward", "Weekend spending reward: ₹250 for spending ₹3000 on weekend.", "weekend@bank.com", "NOT_EXPENSE"],
    ["Festival spending reward", "Holi spending reward: ₹500 for spending ₹5000 during Holi.", "festival@bank.com", "NOT_EXPENSE"],
    ["New month reward", "New month reward: ₹100 for completing 5 transactions in April.", "newmonth@bank.com", "NOT_EXPENSE"],
    ["Consistent spender reward", "Consistent spender reward: ₹400 for spending ₹20000 for 3 consecutive months.", "spend@bank.com", "NOT_EXPENSE"],
    ["Big spender reward", "Big spender reward: ₹750 for spending ₹75000 in a single transaction.", "big@bank.com", "NOT_EXPENSE"],
    ["Multi-category reward", "Multi-category reward: ₹200 for spending on 5 different categories.", "multi@bank.com", "NOT_EXPENSE"],
    ["Partner app reward", "Partner app reward: ₹150 for completing transactions on partner app.", "partner@bank.com", "NOT_EXPENSE"],
]


def create_expanded_dataset(input_csv: Path, output_csv: Path, all_samples: list) -> dict:
    """Create expanded dataset with additional samples."""
    existing_rows = []
    
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing_rows.append(row)
    
    for sample in all_samples:
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
        "original_count": 1000,
        "samples_added": len(all_samples),
        "final_count": len(existing_rows),
        "label_distribution": label_counts
    }


def print_expansion_report(stats: dict) -> None:
    """Print expansion report."""
    print("\n" + "=" * 60)
    print("DATASET EXPANDED WITH CREDIT CARD BILLS & MORE")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Original count: {stats['original_count']}")
    print(f"   Samples added: {stats['samples_added']}")
    print(f"   Final count: {stats['final_count']}")
    
    print(f"\n📈 Label Distribution:")
    for label, count in stats["label_distribution"].items():
        percentage = (count / stats["final_count"]) * 100
        print(f"   {label}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Combine all samples
    all_samples = (
        CREDIT_CARD_BILL_SAMPLES +
        BILL_STATEMENT_SAMPLES +
        LOAN_EMI_SAMPLES +
        INSURANCE_PREMIUM_SAMPLES +
        SUBSCRIPTION_SAMPLES +
        NOT_EXPENSE_NOTIFICATIONS
    )
    
    stats = create_expanded_dataset(TRAINING_CSV, EXPANDED_CSV, all_samples)
    print_expansion_report(stats)
