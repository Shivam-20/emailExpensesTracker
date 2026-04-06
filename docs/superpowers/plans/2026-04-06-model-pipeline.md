# Model Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multiple model pipeline (MiniLM-L6-V2, TinyBERT, ALBERT, MobileBERT, DistilBERT, TF-IDF/NB) with ensemble voting and cascade fallback modes, with UI in Settings tab.

**Architecture:** 
- New `classifier/pipeline.py` module handles model loading, ensemble voting, cascade fallback
- New `classifier/lightweight_models.py` wraps MiniLM/TinyBERT/ALBERT/MobileBERT training and inference
- Settings tab gets new "Model Pipeline" section for UI
- Pipeline config persisted in `data/pipeline_config.json`

**Tech Stack:** PyQt6, sentence-transformers, transformers, sklearn

---

## File Structure

- Create: `classifier/lightweight_models.py` - MiniLM/TinyBERT/ALBERT/MobileBERT wrappers
- Create: `classifier/pipeline.py` - Ensemble/cascade pipeline logic
- Modify: `classifier/config.py` - Add pipeline config paths
- Modify: `tabs/settings_tab.py` - Add pipeline UI section
- Modify: `classifier/router.py` - Integrate pipeline
- Create: `tests/test_pipeline.py` - Pipeline tests

---

### Task 1: Create lightweight_models.py - MiniLM/TinyBERT/ALBERT/MobileBERT wrappers

**Files:**
- Create: `classifier/lightweight_models.py`
- Test: `tests/test_lightweight_models.py`

- [ ] **Step 1: Write the model support definitions**

```python
# classifier/lightweight_models.py

from enum import Enum
from pathlib import Path
from typing import Optional

MODEL_CONFIGS = {
    "minilm-l6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-V2",
        "params": "22M",
        "description": "Fastest, great accuracy",
    },
    "tinybert": {
        "name": "huawei-noah/TinyBERT_General_4L_312D",
        "params": "14M",
        "description": "Smaller than DistilBERT",
    },
    "albert": {
        "name": "albert-base-v2",
        "params": "12M",
        "description": "Parameter sharing, memory efficient",
    },
    "mobilebert": {
        "name": "google/mobilebert-uncased",
        "params": "25M",
        "description": "Optimized for mobile/CPU",
    },
    "distilbert": {
        "name": "distilbert-base-uncased",
        "params": "67M",
        "description": "Original DistilBERT",
    },
}

class LightweightModelType(Enum):
    MINILM = "minilm-l6-v2"
    TINYBERT = "tinybert"
    ALBERT = "albert"
    MOBILEBERT = "mobilebert"
    DISTILBERT = "distilbert"

# Functions to train and predict for each model type
def train_model(model_type: str, csv_path: Path, model_dir: Path) -> None:
    """Train the specified model type on csv_path data."""
    pass

def predict(model_type: str, subject: str, sender: str, body: str) -> dict:
    """Predict using the specified model type."""
    pass

def load_model(model_type: str, model_dir: Path):
    """Load a trained model for inference."""
    pass
```

- [ ] **Step 2: Implement training logic for MiniLM**

```python
def train_minilm(csv_path: Path, model_dir: Path) -> None:
    """Train MiniLM model on classification task."""
    from sentence_transformers import SentenceTransformer, InputExample, LoggingHandler
    from sklearn.linear_model import LogisticRegression
    import logging
    
    # Load training data
    df = pd.read_csv(csv_path)
    train_examples = []
    for _, row in df.iterrows():
        text = f"{row['subject']} {row['sender']} {row['body']}"
        label = row['label']
        train_examples.append(InputExample(texts=[text], label=label))
    
    # Create embeddings
    model = SentenceTransformer('all-MiniLM-L6-V2')
    train_embeddings = model.encode([ex.texts[0] for ex in train_examples])
    train_labels = [ex.label for ex in train_examples]
    
    # Train classifier
    clf = LogisticRegression(max_iter=1000)
    clf.fit(train_embeddings, train_labels)
    
    # Save
    import joblib
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "miniLM_embeddings.joblib")
    joblib.dump(clf, model_dir / "miniLM_classifier.joblib")
```

- [ ] **Step 3: Implement prediction for MiniLM**

```python
def predict_minilm(subject: str, sender: str, body: str) -> dict:
    """Predict using MiniLM model."""
    from classifier.lightweight_models import _load_minilm
    import joblib
    
    model_dir = Path("models/lightweight")
    emb_model, clf = _load_minilm(model_dir)
    
    text = f"{subject} {sender} {body}"
    embedding = emb_model.encode([text])
    probs = clf.predict_proba(embedding)[0]
    pred = clf.predict(embedding)[0]
    
    confidence = max(probs)
    return {
        "label": pred,
        "confidence": confidence,
        "probas": dict(zip(clf.classes_, probs)),
    }
```

- [ ] **Step 4: Add similar implementations for TinyBERT, ALBERT, MobileBERT**

- [ ] **Step 5: Test training and prediction**

Run: `python3 -c "from classifier.lightweight_models import train_model; train_model('minilm-l6-v2', 'data/training_emails.csv', 'models/lightweight')"`
Expected: Model trained and saved

- [ ] **Step 6: Commit**

```bash
git add classifier/lightweight_models.py
git commit -m "feat: add lightweight models (MiniLM, TinyBERT, ALBERT, MobileBERT)"
```

---

### Task 2: Create pipeline.py - Ensemble/Cascade logic

**Files:**
- Create: `classifier/pipeline.py`
- Modify: `classifier/config.py`

- [ ] **Step 1: Write pipeline configuration**

```python
# classifier/pipeline.py
import json
from enum import Enum
from pathlib import Path
from typing import Optional

PIPELINE_CONFIG_FILE = Path("data/pipeline_config.json")

class PipelineMode(Enum):
    ENSEMBLE = "ensemble"      # Majority voting
    CASCADE = "cascade"        # Fallback to next model

class Pipeline:
    def __init__(self, models: list[str], mode: PipelineMode):
        self.models = models  # List of model names in order
        self.mode = mode
    
    def predict(self, subject: str, sender: str, body: str) -> dict:
        """Run prediction through pipeline."""
        if self.mode == PipelineMode.ENSEMBLE:
            return self._ensemble_predict(subject, sender, body)
        else:
            return self._cascade_predict(subject, sender, body)
    
    def _ensemble_predict(self, subject: str, sender: str, body: str) -> dict:
        """Ensemble: all models vote, majority wins."""
        votes = {"EXPENSE": 0, "NOT_EXPENSE": 0}
        confidences = []
        
        for model in self.models:
            result = _predict_with_model(model, subject, sender, body)
            votes[result["label"]] += 1
            confidences.append(result["confidence"])
        
        # Majority vote
        final_label = "EXPENSE" if votes["EXPENSE"] >= votes["NOT_EXPENSE"] else "NOT_EXPENSE"
        avg_confidence = sum(confidences) / len(confidences)
        
        return {
            "label": final_label,
            "confidence": avg_confidence,
            "votes": votes,
            "mode": "ensemble",
        }
    
    def _cascade_predict(self, subject: str, sender: str, body: str) -> dict:
        """Cascade: use first model with confidence >= threshold."""
        THRESHOLD = 0.80
        
        for model in self.models:
            result = _predict_with_model(model, subject, sender, body)
            if result["confidence"] >= THRESHOLD:
                result["mode"] = "cascade"
                result["used_model"] = model
                return result
        
        # All models below threshold - return best effort
        best = max([_predict_with_model(m, subject, sender, body) for m in self.models], 
                   key=lambda x: x["confidence"])
        best["mode"] = "cascade"
        best["fallback"] = True
        return best
```

- [ ] **Step 2: Add pipeline config persistence**

```python
def load_pipeline_config() -> dict:
    """Load pipeline configuration from file."""
    if PIPELINE_CONFIG_FILE.exists():
        return json.loads(PIPELINE_CONFIG_FILE.read_text())
    return {
        "mode": "ensemble",
        "active_models": ["minilm-l6-v2", "tfidf-nb"],
    }

def save_pipeline_config(config: dict) -> None:
    """Save pipeline configuration."""
    PIPELINE_CONFIG_FILE.write_text(json.dumps(config, indent=2))
```

- [ ] **Step 3: Test pipeline**

Run: `python3 -c "from classifier.pipeline import Pipeline, PipelineMode; p = Pipeline(['minilm-l6-v2', 'tfidf-nb'], PipelineMode.ENSEMBLE); print(p.predict('Invoice for order #123', 'sender@test.com', 'Please pay Rs. 500'))"`
Expected: Prediction result

- [ ] **Step 4: Commit**

```bash
git add classifier/pipeline.py classifier/config.py
git commit -m "feat: add ensemble/cascade pipeline logic"
```

---

### Task 3: Update Settings Tab with Pipeline UI

**Files:**
- Modify: `tabs/settings_tab.py`

- [ ] **Step 1: Add pipeline section to settings tab**

```python
def _build_pipeline_section(self) -> QGroupBox:
    box = QGroupBox("🤖 Model Pipeline")
    layout = QVBoxLayout(box)
    
    # Mode selection
    mode_layout = QHBoxLayout()
    mode_layout.addWidget(QLabel("Pipeline Mode:"))
    self._pipeline_mode_combo = QComboBox()
    self._pipeline_mode_combo.addItems(["Ensemble Voting", "Cascade Fallback"])
    self._pipeline_mode_combo.currentTextChanged.connect(self._on_pipeline_mode_changed)
    mode_layout.addWidget(self._pipeline_mode_combo)
    mode_layout.addStretch()
    layout.addLayout(mode_layout)
    
    # Model list
    self._pipeline_table = QTableWidget()
    self._pipeline_table.setColumnCount(4)
    self._pipeline_table.setHorizontalHeaderLabels(["Model", "Status", "Train", "Remove"])
    self._pipeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self._pipeline_table.setMaximumHeight(200)
    layout.addWidget(self._pipeline_table)
    
    # Buttons
    btn_layout = QHBoxLayout()
    self._add_model_btn = QPushButton("+ Add Model")
    self._add_model_btn.clicked.connect(self._on_add_model_clicked)
    self._save_pipeline_btn = QPushButton("Save Pipeline")
    self._save_pipeline_btn.clicked.connect(self._on_save_pipeline_clicked)
    btn_layout.addWidget(self._add_model_btn)
    btn_layout.addWidget(self._save_pipeline_btn)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)
    
    return box
```

- [ ] **Step 2: Add pipeline signals**

```python
# In __init__
self.pipeline_changed = pyqtSignal(dict)  # Emit when pipeline config changes
```

- [ ] **Step 3: Implement model management**

```python
def _load_pipeline_models(self):
    """Load available models and their status."""
    from classifier.lightweight_models import MODEL_CONFIGS
    
    models = [
        ("MiniLM-L6-V2", "minilm-l6-v2"),
        ("TinyBERT", "tinybert"),
        ("ALBERT", "albert"),
        ("MobileBERT", "mobilebert"),
        ("DistilBERT", "distilbert"),
        ("TF-IDF/NB", "tfidf-nb"),
    ]
    
    # Check which models are trained
    # Update table with status
```

- [ ] **Step 4: Test UI loads**

Run: Launch app, check Settings tab shows new pipeline section

- [ ] **Step 5: Commit**

```bash
git add tabs/settings_tab.py
git commit -m "feat: add model pipeline UI to settings tab"
```

---

### Task 4: Integrate pipeline with classifier router

**Files:**
- Modify: `classifier/router.py`

- [ ] **Step 1: Update router to use pipeline**

```python
def _classify_with_stage3(self, email: EmailInput) -> dict:
    """Stage 3: Use pipeline for final classification."""
    from classifier.pipeline import load_pipeline_config, Pipeline, PipelineMode
    
    config = load_pipeline_config()
    
    if not config.get("active_models"):
        # Fallback to default
        return self._classify_distilbert(email)
    
    mode = PipelineMode.CASCADE if config["mode"] == "cascade" else PipelineMode.ENSEMBLE
    pipeline = Pipeline(config["active_models"], mode)
    
    return pipeline.predict(email.subject, email.sender, email.body)
```

- [ ] **Step 2: Test integration**

Run: `python3 -c "from classifier.router import ClassifierRouter; r = ClassifierRouter(); print(r.classify('Invoice #123', 'test@test.com', 'Please pay Rs. 500'))"`

- [ ] **Step 3: Commit**

```bash
git add classifier/router.py
git commit -m "feat: integrate pipeline with classifier router"
```

---

### Task 5: Add training scripts for each model

**Files:**
- Modify: `scripts/train_classifier.sh`

- [ ] **Step 1: Add model-specific training options**

```bash
# Add to train_classifier.sh
if [ "$arg" = "--minilm" ]; then
    USE_MINILM=true
fi
# ... same for tinybert, albert, mobilebert, distilbert
```

- [ ] **Step 2: Add training functions**

```bash
if $USE_MINILM; then
    echo "Training MiniLM-L6-V2..."
    python3 -c "
import sys; sys.path.insert(0, '.')
from classifier.lightweight_models import train_model
from classifier.config import TRAINING_CSV, LIGHTWEIGHT_MODELS_DIR
train_model('minilm-l6-v2', TRAINING_CSV, LIGHTWEIGHT_MODELS_DIR)
"
fi
```

- [ ] **Step 3: Commit**

```bash
git add scripts/train_classifier.sh
git commit -m "feat: add training options for all lightweight models"
```

---

### Task 6: End-to-end test

**Files:**
- No new files

- [ ] **Step 1: Train all default pipeline models**

Run: 
```bash
bash scripts/train_classifier.sh --minilm
bash scripts/train_classifier.sh
```

- [ ] **Step 2: Test pipeline prediction**

```bash
python3 -c "
from classifier.pipeline import Pipeline, PipelineMode, load_pipeline_config, save_pipeline_config

# Setup config
config = {'mode': 'ensemble', 'active_models': ['minilm-l6-v2', 'tfidf-nb']}
save_pipeline_config(config)

# Test
p = Pipeline(['minilm-l6-v2', 'tfidf-nb'], PipelineMode.ENSEMBLE)
result = p.predict('Invoice for order #123', 'sender@amazon.com', 'Amount: Rs. 599')
print(result)
"
```

Expected: Valid prediction with confidence

- [ ] **Step 3: Commit**

```bash
git commit -m "test: verify pipeline end-to-end"
```

---

## Summary

Total Tasks: 6
- Task 1: Lightweight models (MiniLM, TinyBERT, ALBERT, MobileBERT)
- Task 2: Pipeline logic (ensemble/cascade)
- Task 3: Settings UI
- Task 4: Router integration
- Task 5: Training scripts
- Task 6: End-to-end test
