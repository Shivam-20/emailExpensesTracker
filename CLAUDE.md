# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gmail Expense Tracker v2 — a PyQt6 desktop app (Ubuntu 22.04+, Python 3.10+) that reads Gmail via OAuth2 (read-only), extracts expense data from emails, classifies them with a hybrid 3-stage AI pipeline, and presents analytics with charts, trends, and CSV exports. Uses SQLite for caching/offline browsing and a Catppuccin-inspired dark theme.

## Commands

```bash
# Setup (one-time: creates venv, installs deps, trains ML models)
bash scripts/setup.sh

# Run
python3 main.py                    # Direct launch
bash scripts/start.sh              # Background launch (PID in .app.pid)
bash scripts/stop.sh               # Stop background instance

# Tests
pytest tests/ -v                   # Run all tests
pytest tests/test_rules.py -v      # Single test file

# Train/retrain classifier
bash scripts/train_classifier.sh              # Train TF-IDF + Naive Bayes
bash scripts/train_classifier.sh --retrain    # Merge feedback.csv + retrain NB
bash scripts/train_classifier.sh --distilbert # Fine-tune DistilBERT
```

## Architecture

### Module Responsibilities

- **`classifier/`** — 3-stage AI pipeline (no UI dependencies). `router.py` orchestrates: Stage 1 (rules.py: keyword scoring) → Stage 2 (ml_model.py: TF-IDF + Naive Bayes) → Stage 3 (distilbert_model.py or ollama_fallback.py). All thresholds live in `config.py`.
- **`core/`** — Data logic: `gmail_auth.py` (OAuth2), `db.py` (SQLite schema + CRUD), `expense_parser.py` (amount/currency/payment/category extraction), `deduplicator.py`, `csv_exporter.py`.
- **`tabs/`** — PyQt6 tab views: expenses table, 2x2 charts (matplotlib), month-over-month trends, settings (budgets, ignore list, custom rules, AI backend selector).
- **`workers/`** — QThread workers. `gmail_worker.py` does background fetch/parse/deduplicate/cache, communicates via Qt signals.
- **`config/`** — Static mappings: `category_map.py` (vendor keywords → categories), `payment_patterns.py` (payment method regexes).
- **`scripts/`** — Bash automation for setup, start/stop, and ML training.

### Classifier Pipeline Flow

```
Stage 1 (rules): score >= 6 → EXPENSE (high) | score == 0 → NOT_EXPENSE | else → Stage 2
Stage 2 (TF-IDF+NB): prob >= 0.85 → high | 0.55–0.85 → medium | < 0.55 → Stage 3
Stage 3 (DistilBERT or phi4-mini): final classification | uncertain → REVIEW
```

Thresholds are centralized in `classifier/config.py`. Stage 3 backend is user-configurable (persisted in `data/classifier_settings.json`).

### Data Flow

1. OAuth2 auth → Gmail API (read-only scope)
2. GmailWorker fetches messages by month/label in background thread
3. expense_parser extracts amounts, currency, payment method, category
4. classifier pipeline assigns EXPENSE/NOT_EXPENSE/REVIEW + confidence
5. Results upserted to SQLite (`core/db.py`), preserving user edits
6. UI tabs read from DB; user edits write back to DB

### Database

SQLite with WAL mode. Three tables: `expenses` (keyed by Gmail message ID, stores parsed data + user overrides via `amount_edited`/`category_edited` fields), `ignore_list` (sender/subject blacklist), `budgets` (per-category limits). Schema auto-migrates missing columns on startup.

### UI Threading

All Gmail API calls and parsing run in `GmailWorker` (QThread). Communication to MainWindow is via Qt signals only — never access UI widgets from worker threads.

## Key Conventions

- Entry point is `main.py` which shows a first-run dialog for data directory selection (stored in `~/.expense-tracker-path`)
- User-edited fields (`amount_edited`, `category_edited`) are preserved across re-fetches in `db.py:upsert_expenses()`
- Classification audit trail logged to `logs/classification_audit.csv`
- Confidence bands: HIGH (>0.85), MEDIUM (0.55–0.85), LOW (<0.55)
- Currency defaults to INR; supports USD, EUR, GBP detection
- Secrets (`credentials.json`, `token.json`, `*.db`) are gitignored — never commit these
