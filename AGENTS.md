# AGENTS.md

## Build/Lint/Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_rules.py -v

# Run specific test function
pytest tests/test_rules.py::test_clear_invoice_email_scores_high -v

# Train ML model
bash scripts/train_classifier.sh

# Retrain with user feedback
bash scripts/train_classifier.sh --retrain

# Fine-tune DistilBERT
bash scripts/train_classifier.sh --distilbert

# Setup (venv, deps, training)
bash scripts/setup.sh

# Run app
python3 main.py
```

**Note**: No automated lint/typecheck configured. Before completing work, manually run `pytest tests/ -v` and ensure tests pass.

## Code Style Guidelines

### Imports
- Standard library → third-party → local imports (each group separated by blank line)
- In tests: `sys.path.insert(0, str(Path(__file__).parent.parent))` to enable root imports
- Example:
```python
import logging
from pathlib import Path

from PyQt6.QtCore import QThread

from classifier.schemas import EmailInput
```

### Naming Conventions
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `RULE_HIGH_THRESHOLD`, `MAX_MESSAGES`)
- **Functions/Methods**: `snake_case` (e.g., `score_email`, `get_data_dir`)
- **Classes**: `PascalCase` (e.g., `Database`, `EmailInput`, `GmailWorker`)
- **Private functions**: `_leading_underscore` (e.g., `_run`, `_migrate`)
- **Instance variables**: `self._private_var` for internal state, `self.public_var` otherwise

### Type Hints
- Required on all function signatures: `def foo(x: str) -> None:`
- Use `Optional[T]` for nullable returns
- Use `Literal` for constrained strings: `Literal["EXPENSE", "NOT_EXPENSE", "REVIEW"]`
- Pathlib for file paths: `Path` instead of `str`
- Example:
```python
from typing import Optional, Literal
from pathlib import Path

def upsert_expenses(self, rows: list[dict]) -> int: ...

def get_data_dir() -> Optional[Path]: ...
```

### Error Handling
- Use specific exceptions: `ValueError`, `RuntimeError`, `sqlite3.IntegrityError`
- Log errors with appropriate level: `logger.exception()`, `logger.warning()`
- Provide fallback values on recoverable errors (never silently fail critical paths)
- For QThread workers: emit error signals: `self.error.emit(f"Unexpected error: {exc}")`
- Example:
```python
try:
    result = operation()
except OSError as exc:
    logger.warning("Failed to load config: %s", exc)
    return DEFAULT_VALUE
```

### Data Structures
- Use `@dataclass` for data models with minimal behavior
- Use `field(default_factory=list)` for mutable defaults in dataclasses
- SQLite: use `sqlite3.Row` with `row_factory` for dict-like access
- Example:
```python
from dataclasses import dataclass, field

@dataclass
class EmailInput:
    subject: str
    body: str
    sender: str
    attachments: list[str] = field(default_factory=list)
```

### Formatting & Structure
- Module docstring describes purpose (first line of file)
- Function docstrings: concise, no arguments listed in header
- Section dividers: `# ── Section Name ──────────────────────────────────────`
- Private methods grouped together under `# ── Private helpers ──`
- Max line length: 100-120 characters
- Blank lines between methods (2 blank lines for top-level, 1 for nested)

### Logging
- Module-level: `logger = logging.getLogger(__name__)`
- Levels: `debug()` for diagnostics, `info()` for significant events, `warning()` for recoverable issues, `exception()` for errors
- No print statements — use logger instead

### Testing
- Use `pytest` framework
- Test files: `tests/test_*.py`
- Test functions: `def test_feature_behavior() -> None:`
- Use `unittest.mock.patch` for mocking
- Clear descriptions in docstrings
- Group related tests with section dividers
- Example:
```python
def test_clear_invoice_email_scores_high() -> None:
    """A clear invoice email should score >= RULE_HIGH_THRESHOLD (6)."""
    score = score_email(subject="Invoice #123", body="...", sender="...")
    assert score >= 6
```

### Threading (PyQt6)
- Background work in QThread (`workers/` directory)
- Never access UI widgets from worker threads
- Communicate via Qt signals only: `progress.emit()`, `finished.emit()`, `error.emit()`
- Wrap thread entry in try/except to prevent silent failures

### Database
- All DB operations in `core/db.py` or called from QThread (never main thread)
- Use parameterized queries to prevent SQL injection
- Connection with WAL mode: `PRAGMA journal_mode=WAL`
- Auto-migrations: check for missing columns on startup
- Example:
```python
self.conn.execute("SELECT * FROM expenses WHERE id=?", (msg_id,))
```

### Constants
- Centralize magic numbers in `classifier/config.py` or module-level constants
- Do not hardcode thresholds elsewhere — import from config
- Example: `from classifier.config import RULE_HIGH_THRESHOLD`
