# Gmail Expense Tracker v2

A production-quality **PyQt6 desktop app** for Ubuntu that connects to Gmail via OAuth2,
extracts expense emails, classifies them with a hybrid AI pipeline, and generates monthly
reports with charts, trends, and CSV export.

---

## Features

- 🔐 Google OAuth2 (read-only Gmail access)
- 🤖 **Hybrid AI classifier** — Rules → ML (TF-IDF + Naive Bayes) → Stage 3 (DistilBERT or phi4-mini)
- 📦 **SQLite cache** — fetch once, browse offline
- 💡 **Confidence scoring** — HIGH / MEDIUM / LOW per transaction
- 💳 **Payment method detection** — UPI, Credit Card ••1234, Net Banking, Wallet, COD
- 🔁 **Automatic deduplication** — flags likely duplicate emails
- 🏷️ **Tag system** — add custom tags, filter by them
- 📊 **4 charts**: Category pie · Top-10 bar · Payment donut · Daily heatmap
- 📈 **Trends tab** — month-over-month line chart + comparison table
- ⚙️ **Settings**: budgets, ignore list, custom keyword rules
- 🌑 Dark theme (Catppuccin-inspired)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| pip | latest |
| Ubuntu | 22.04+ |
| Ollama *(optional)* | latest — for phi4-mini Stage 3 |
| CUDA/CPU | CPU-only is fine for DistilBERT |

---

## Quick Start

```bash
cd gmail_expense_tracker

# 1. One-time setup (venv, deps, ML model training)
bash scripts/setup.sh

# 2. Place credentials.json (see section below)

# 3. Launch the app
bash scripts/start.sh

# 4. Stop the app
bash scripts/stop.sh
```

---

## Installation

```bash
# Clone or download
cd gmail_expense_tracker

# (Recommended) virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Train the ML classifier (first time)
bash scripts/train_classifier.sh
```

---

## Getting `credentials.json`

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and sign in.
2. **Create project** → give it a name → **Create**.
3. **APIs & Services → Library** → search **Gmail API** → **Enable**.
4. **APIs & Services → OAuth consent screen**
   - Choose **External** → **Create**
   - Fill in App name, support email, developer email
   - **Save and Continue** through all steps
   - On **Test users** screen: add your Gmail address
5. **APIs & Services → Credentials**
   - **+ Create Credentials → OAuth client ID**
   - Application type: **Desktop app** → **Create**
   - Click **⬇ Download JSON**
6. Rename downloaded file to **`credentials.json`**
7. Place in the same directory as `main.py`

```
gmail_expense_tracker/
├── credentials.json   ← here
├── main.py
└── …
```

---

## Running

```bash
# Start (recommended — background, writes logs/app.log)
bash scripts/start.sh

# Or run directly in terminal
python3 main.py

# Stop background instance
bash scripts/stop.sh
```

### First launch
1. Choose where to store app data (SQLite DB, token, config)
2. The choice is saved to `~/.expense-tracker-path`

### Connect Gmail
1. Click **🔑 Connect Gmail** in the sidebar
2. Browser opens → sign in → grant read-only access
3. `token.json` is saved to your data directory

### Fetch expenses
1. Select **Year** and **Month**
2. Optionally select a **Gmail Label** (e.g. "Transactions" for precision)
3. Click **�� Fetch Expenses**
4. Results cached in SQLite — subsequent opens use cache instantly

---

## Tips

- Create a Gmail filter: receipts/invoices → label "Transactions"
- Select "Transactions" label before fetching for faster, cleaner results
- Use **⚙️ Settings → Custom Rules** to teach the app your specific vendors
- **🔄 Refresh Cache** to force a re-fetch from Gmail

---

## File Structure

```
gmail_expense_tracker/
├── main.py                     # Entry point + first-run dialog
├── main_window.py              # QMainWindow, sidebar, tab wiring
├── styles.py                   # Dark theme + QSS
├── requirements.txt
├── README.md
│
├── scripts/                    # Helper shell scripts
│   ├── setup.sh                # One-time setup (venv, deps, ML training)
│   ├── start.sh                # Launch app (background, PID tracked)
│   ├── stop.sh                 # Gracefully stop background instance
│   └── train_classifier.sh     # Train / retrain the ML model
│
├── classifier/                 # AI classifier pipeline (Rules → ML → LLM)
│   ├── __init__.py             # Public API: classify(EmailInput)
│   ├── config.py               # All thresholds and settings
│   ├── schemas.py              # EmailInput + ClassificationResult dataclasses
│   ├── preprocess.py           # Text cleaning, feature extraction
│   ├── rules.py                # Stage 1: keyword scoring engine
│   ├── ml_model.py             # Stage 2: TF-IDF + Naive Bayes
│   ├── ollama_fallback.py      # Stage 3 Option B: phi4-mini via Ollama
│   ├── distilbert_model.py     # Stage 3 Option A: DistilBERT fine-tuned
│   ├── router.py               # Pipeline orchestrator
│   ├── cache.py                # SQLite LLM result cache
│   ├── audit.py                # CSV classification audit log
│   └── utils.py                # Shared helpers
│
├── tabs/
│   ├── expenses_tab.py         # Table, chips, bulk actions, context menu
│   ├── charts_tab.py           # 2×2 matplotlib charts
│   ├── trends_tab.py           # Month-over-month line chart
│   └── settings_tab.py         # Budgets, ignore list, custom rules, AI backend
│
├── workers/
│   └── gmail_worker.py         # QThread fetch/parse/cache
│
├── core/
│   ├── db.py                   # SQLite schema + CRUD (+ classifier fields)
│   ├── expense_parser.py       # Amount, confidence, payment method + classifier
│   ├── deduplicator.py         # Duplicate detection
│   ├── gmail_auth.py           # OAuth2 + label listing
│   └── csv_exporter.py         # CSV export
│
├── config/
│   ├── category_map.py         # Built-in vendor → category map
│   └── payment_patterns.py     # Payment method regex patterns
│
├── data/
│   ├── training_emails.csv     # Labeled training data for ML model
│   ├── feedback.csv            # User corrections (created on first correction)
│   └── cached_predictions.db   # SQLite LLM result cache
│   └── classifier_settings.json# Persisted Stage 3 backend choice
│
├── models/
│   ├── nb_tfidf_model.joblib   # Trained TF-IDF + Naive Bayes model
│   └── distilbert/             # Fine-tuned DistilBERT model (after training)
│
├── logs/
│   ├── app.log                 # Application runtime log
│   └── classification_audit.csv# Every classification decision logged here
│
└── tests/
    ├── test_rules.py
    ├── test_ml_model.py
    ├── test_router.py
    ├── test_ollama_fallback.py
    └── test_distilbert_model.py
```

---

## AI Classifier Pipeline

Every email passes through a 3-stage pipeline before being shown in the table:

```
Stage 1 → rules.py        Always runs. Score keywords (< 5 ms).
              ↓ score >= 6 → EXPENSE
              ↓ score == 0 → NOT_EXPENSE (skipped)
              ↓ 1–5        → escalate to Stage 2

Stage 2 → ml_model.py     TF-IDF + Naive Bayes (< 50 ms).
              ↓ prob >= 0.85 → accept
              ↓ prob >= 0.55 → accept (medium confidence)
              ↓ prob <  0.55 → escalate to Stage 3

Stage 3 → distilbert_model  DistilBERT fine-tuned (default, ~200 ms, CPU-only)
       OR  ollama_fallback   phi4-mini via Ollama (zero-shot, no training needed)
              ↓ high/medium band → accept
              ↓ low band         → REVIEW

Fallback → REVIEW          Shown in table with 🔍 badge
```

### Switching Stage 3 backend

Go to **⚙️ Settings → Stage 3 AI Backend** and choose:

| Backend | Speed | Requirements | Best For |
|---|---|---|---|
| **DistilBERT** *(default)* | ~200 ms/email | `torch`, `transformers` | Fast, offline, CPU-only |
| **phi4-mini** | 5–8 s/email | Ollama running locally | Ambiguous/unseen senders |

The selection is persisted to `data/classifier_settings.json`. The sidebar shows
the active backend with a live Ollama status indicator.

| Label | Behaviour |
|---|---|
| `EXPENSE` | Added to the table normally |
| `NOT_EXPENSE` | Silently skipped |
| `REVIEW` | Added with `status = review`, flagged for manual check |

### Retraining the model

```bash
# Retrain TF-IDF + Naive Bayes (Stage 2)
bash scripts/train_classifier.sh --retrain

# Fine-tune DistilBERT on training data (Stage 3 Option A)
bash scripts/train_classifier.sh --distilbert

# DistilBERT retrain with user feedback merged
bash scripts/train_classifier.sh --distilbert --retrain
```

### LLM fallback (optional — Stage 3 Option B)

Stage 3 phi4-mini requires [Ollama](https://ollama.com) running locally:

```bash
# Install Ollama, then:
ollama serve
ollama pull phi4-mini
```

If Ollama is not installed or not running, Stage 3 will return REVIEW for
uncertain emails. Switch to DistilBERT in Settings to avoid this.

---

## Scripts Reference

| Script | Purpose |
|---|---|
| `bash scripts/setup.sh` | One-time setup: venv, deps, ML training, DistilBERT tokenizer cache, phi4-mini pull |
| `bash scripts/start.sh` | Launch app in background (PID saved to `.app.pid`) |
| `bash scripts/stop.sh` | Stop the background instance gracefully |
| `bash scripts/train_classifier.sh` | Train TF-IDF + NB model from `data/training_emails.csv` |
| `bash scripts/train_classifier.sh --retrain` | Merge `data/feedback.csv` and retrain NB |
| `bash scripts/train_classifier.sh --distilbert` | Fine-tune DistilBERT on training data |
| `bash scripts/train_classifier.sh --distilbert --retrain` | DistilBERT retrain with feedback |

---

## Running Tests

```bash
pytest tests/ -v
```

---



- Scope: `gmail.readonly` — cannot send, delete, or modify any email
- `credentials.json` and `token.json` stored **locally only**
- No data sent to any third-party server

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `credentials.json not found` | Download from Google Cloud Console (see above) |
| Browser doesn't open | Run from a desktop terminal (not SSH/headless) |
| No expenses found | Try a different month; check Gmail manually |
| `ModuleNotFoundError` | Run `bash scripts/setup.sh` or `pip install -r requirements.txt` |
| Charts blank after resize | Switch tabs and back to trigger redraw |
| ML model missing | Run `bash scripts/train_classifier.sh` |
| DistilBERT model missing | Run `bash scripts/train_classifier.sh --distilbert` |
| LLM stage skipped | Install Ollama + `ollama pull phi4-mini`, or switch to DistilBERT in Settings |
| Too many REVIEW emails | Add corrections to `data/feedback.csv` and run `--retrain` |

---

## License

MIT
