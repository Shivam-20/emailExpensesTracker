# Email Category Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-category email classification with financial, communication, and system categories, with semi-automatic labeling and custom category support.

**Architecture:**
- New category classifier model (extend existing ML pipeline)
- Category training data with 12 categories
- UI for category display and manual adjustment
- Auto-learning from user corrections

**Tech Stack:** PyQt6, sklearn, sentence-transformers

---

## File Structure

- Create: `data/category_training.csv` - Training data for 12 categories
- Modify: `classifier/pipeline.py` - Add category classification
- Modify: `config/category_map.py` - Add new category definitions
- Modify: `tabs/expenses_tab.py` - Show category suggestions
- Create: `tests/test_category_classifier.py` - Category tests

---

### Task 1: Create category training data

**Files:**
- Create: `data/category_training.csv`
- Test: Verify CSV structure

- [ ] **Step 1: Create CSV with 12 categories**

```bash
# Create data/category_training.csv with columns:
# subject, body, sender, category

# Categories:
# EXPENSE, INCOME, INVESTMENT, BILLS, JOB, NEWS, SOCIAL, IMPORTANT, PROMOTIONS, PERSONAL, ORDERS, ACCOUNT
```

- [ ] **Step 2: Add 50+ samples per category**

Add diverse email examples for each of the 12 categories.

- [ ] **Step 3: Test CSV loads**

Run: `python3 -c "import pandas as pd; df = pd.read_csv('data/category_training.csv'); print(df['category'].value_counts())"`
Expected: ~50 samples per category

- [ ] **Step 4: Commit**

```bash
git add data/category_training.csv
git commit -m "feat: add category training data with 12 categories"
```

---

### Task 2: Create category classifier

**Files:**
- Create: `classifier/category_classifier.py`
- Test: `tests/test_category_classifier.py`

- [ ] **Step 1: Write category classifier module**

```python
# classifier/category_classifier.py

from pathlib import Path
from typing import Optional

CATEGORIES = [
    "EXPENSE", "INCOME", "INVESTMENT", "BILLS", 
    "JOB", "NEWS", "SOCIAL", "IMPORTANT", 
    "PROMOTIONS", "PERSONAL", "ORDERS", "ACCOUNT"
]

def train_category_model(csv_path: Path, model_dir: Path) -> None:
    """Train category classifier on csv_path."""
    pass

def predict_category(subject: str, body: str, sender: str) -> dict:
    """Predict email category. Returns dict with label, confidence."""
    pass
```

- [ ] **Step 2: Implement using MiniLM embeddings + classifier**

```python
def train_category_model(csv_path: Path, model_dir: Path) -> None:
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    import joblib
    
    df = pd.read_csv(csv_path)
    texts = df['subject'] + ' ' + df['body']
    labels = df['category']
    
    model = SentenceTransformer('all-MiniLM-L6-V2')
    embeddings = model.encode(texts.tolist())
    
    clf = LogisticRegression(max_iter=1000)
    clf.fit(embeddings, labels)
    
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "category_embeddings.joblib")
    joblib.dump(clf, model_dir / "category_classifier.joblib")
```

- [ ] **Step 3: Test prediction**

Run: `python3 -c "from classifier.category_classifier import predict_category; print(predict_category('Salary credited', 'Your salary of Rs.50000 is credited', 'hr@company.com'))"`
Expected: {"label": "INCOME", "confidence": >0.8}

- [ ] **Step 4: Commit**

```bash
git add classifier/category_classifier.py
git commit -m "feat: add category classifier with 12 categories"
```

---

### Task 3: Integrate category classifier into pipeline

**Files:**
- Modify: `classifier/pipeline.py`
- Modify: `classifier/router.py`

- [ ] **Step 1: Add category classification to pipeline**

```python
# In pipeline.py, add:
def classify_category(email_text: str) -> str:
    """Classify email into one of 12 categories."""
    pass
```

- [ ] **Step 2: Update router to use category classifier**

```python
# In router.py, after expense classification:
def classify_with_category(self, email):
    # First classify expense/not-expense
    expense_result = self.classify(email)
    # Then classify category
    category = predict_category(email.subject, email.body, email.sender)
    return {**expense_result, "category": category}
```

- [ ] **Step 3: Commit**

```bash
git add classifier/pipeline.py classifier/router.py
git commit -m "feat: integrate category classifier into pipeline"
```

---

### Task 4: Add category display in UI

**Files:**
- Modify: `tabs/expenses_tab.py`
- Modify: `core/db.py` (add category column)

- [ ] **Step 1: Add category column to expenses table**

```python
# In core/db.py, modify add_expense:
def add_expense(self, ... , category: str = None):
    # Add category to INSERT statement
```

- [ ] **Step 2: Show category in expenses list**

```python
# In tabs/expenses_tab.py, add category column to table:
columns = ["Date", "Subject", "Amount", "Category", "Actions"]
```

- [ ] **Step 3: Add category dropdown for manual selection**

```python
# Add QComboBox with categories in expense form:
self._category_combo = QComboBox()
self._category_combo.addItems(CATEGORIES)
```

- [ ] **Step 4: Commit**

```bash
git add core/db.py tabs/expenses_tab.py
git commit -m "feat: add category display and selection in UI"
```

---

### Task 5: Add category settings

**Files:**
- Modify: `tabs/settings_tab.py`

- [ ] **Step 1: Add custom category management**

```python
def _build_categories_section(self) -> QGroupBox:
    box = QGroupBox("📂 Email Categories")
    # Table showing categories
    # Add/Edit/Delete buttons
    return box
```

- [ ] **Step 2: Add category to pipeline settings**

- [ ] **Step 3: Commit**

```bash
git add tabs/settings_tab.py
git commit -m "feat: add category management in settings"
```

---

### Task 6: Add category analytics

**Files:**
- Modify: `tabs/trends_tab.py`
- Modify: `tabs/charts_tab.py`

- [ ] **Step 1: Add category breakdown chart**

```python
# In charts_tab.py:
def _build_category_chart(self):
    # Pie chart showing emails by category
    pass
```

- [ ] **Step 2: Add category filter in trends**

- [ ] **Step 3: Commit**

```bash
git add tabs/trends_tab.py tabs/charts_tab.py
git commit -m "feat: add category analytics charts"
```

---

### Task 7: End-to-end test

**Files:**
- No new files

- [ ] **Step 1: Train category model**

Run: `python3 -c "from classifier.category_classifier import train_category_model; train_category_model('data/category_training.csv', 'models/category')"`

- [ ] **Step 2: Test full flow**

```python
# Test: Email comes in → classify expense → categorize → show in UI
```

- [ ] **Step 3: Commit**

```bash
git commit -m "test: verify category classification end-to-end"
```

---

## Summary

Total Tasks: 7
- Task 1: Category training data
- Task 2: Category classifier
- Task 3: Pipeline integration
- Task 4: UI display
- Task 5: Settings management
- Task 6: Analytics
- Task 7: End-to-end test