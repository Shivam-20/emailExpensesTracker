"""
tabs/settings_tab.py — Budgets, Ignore List, Custom Rules, Data Management.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QRadioButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from config.category_map import ALL_CATEGORIES
from styles import (
    ACCENT, BORDER, ERROR, SUCCESS, SURFACE, SURFACE2, SURFACE3,
    TEXT, TEXT_DIM, WARNING,
)

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """Tab 4 — Settings: Budgets, Ignore List, Custom Rules, Data Management."""

    data_dir_changed      = pyqtSignal(Path)
    reauth_requested      = pyqtSignal()
    clear_cache_requested = pyqtSignal(str)   # month string or "" for all
    backend_changed       = pyqtSignal(str)   # "distilbert" | "phi4-mini"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db        = None
        self._data_dir: Optional[Path] = None
        self._config:   dict = {}
        self._setup_ui()

    def set_db(self, db, data_dir: Path, config: dict) -> None:
        self._db       = db
        self._data_dir = data_dir
        self._config   = config
        self._load_all()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(14)

        layout.addWidget(self._build_budgets_section())
        layout.addWidget(self._build_ignore_section())
        layout.addWidget(self._build_rules_section())
        layout.addWidget(self._build_ai_backend_section())
        layout.addWidget(self._build_data_section())
        layout.addStretch()

        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Budget section ────────────────────────────────────────────────────────

    def _build_budgets_section(self) -> QGroupBox:
        box = QGroupBox("📊 Budget vs Actual")
        layout = QVBoxLayout(box)

        self._budget_table = QTableWidget()
        self._budget_table.setColumnCount(5)
        self._budget_table.setHorizontalHeaderLabels(
            ["Category", "Budget (₹)", "Spent (₹)", "Progress", "Status"]
        )
        self._budget_table.verticalHeader().setVisible(False)
        self._budget_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._budget_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._budget_table.cellDoubleClicked.connect(self._on_budget_double_click)
        self._budget_table.setMaximumHeight(300)
        layout.addWidget(self._budget_table)

        return box

    def _load_budgets(self) -> None:
        if not self._db:
            return
        budgets   = self._db.get_budgets()
        categories = ALL_CATEGORIES
        self._budget_table.setRowCount(len(categories))

        # Compute actual spend for current displayed month from cached data
        spent_map: dict[str, float] = {}
        if self._db:
            try:
                months = self._db.get_available_months()
                if months:
                    latest = months[-1]
                    rows = self._db.get_month_expenses(latest)
                    for r in rows:
                        if r["status"] == "excluded":
                            continue
                        cat   = r["category_edited"] or r["category"] or "Other"
                        amt   = r["amount_edited"] or r["amount"] or 0
                        spent_map[cat] = spent_map.get(cat, 0) + amt
            except Exception:
                pass

        for row_i, cat in enumerate(categories):
            budget = budgets.get(cat, 0.0)
            spent  = spent_map.get(cat, 0.0)
            pct    = (spent / budget * 100) if budget > 0 else 0
            over   = budget > 0 and spent > budget
            status = "⚠ Over" if over else ("OK" if budget > 0 else "—")

            self._budget_table.setItem(row_i, 0, _item(cat))
            self._budget_table.setItem(row_i, 1, _item(f"₹{budget:,.0f}"))
            self._budget_table.setItem(row_i, 2, _item(f"₹{spent:,.0f}"))

            # Progress bar cell
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(min(int(pct), 100))
            bar.setFormat(f"{pct:.0f}%")
            bar.setTextVisible(True)
            if over:
                bar.setStyleSheet(f"QProgressBar::chunk {{ background: {ERROR}; }}")
            else:
                bar.setStyleSheet(f"QProgressBar::chunk {{ background: {ACCENT}; }}")
            self._budget_table.setCellWidget(row_i, 3, bar)

            status_item = _item(status, center=True)
            if over:
                status_item.setForeground(Qt.GlobalColor.red)
            self._budget_table.setItem(row_i, 4, status_item)

    def _on_budget_double_click(self, row: int, col: int) -> None:
        if col != 1:  # Only budget column is editable
            return
        cat_item = self._budget_table.item(row, 0)
        if not cat_item:
            return
        cat = cat_item.text()

        dlg = _BudgetEditDialog(cat, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_val = dlg.get_value()
            if self._db:
                self._db.set_budget(cat, new_val)
            self._load_budgets()

    # ── Ignore list section ───────────────────────────────────────────────────

    def _build_ignore_section(self) -> QGroupBox:
        box = QGroupBox("🚫 Ignore List")
        layout = QVBoxLayout(box)

        self._ignore_table = QTableWidget()
        self._ignore_table.setColumnCount(4)
        self._ignore_table.setHorizontalHeaderLabels(
            ["Type", "Value", "Ignored On", "Action"]
        )
        self._ignore_table.verticalHeader().setVisible(False)
        hdr = self._ignore_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._ignore_table.setMaximumHeight(200)
        layout.addWidget(self._ignore_table)

        return box

    def _load_ignore_list(self) -> None:
        if not self._db:
            return
        rows = self._db.get_ignore_list()
        self._ignore_table.setRowCount(len(rows))
        for r_i, row in enumerate(rows):
            self._ignore_table.setItem(r_i, 0, _item(row["type"],   center=True))
            self._ignore_table.setItem(r_i, 1, _item(row["value"]))
            self._ignore_table.setItem(r_i, 2, _item(str(row["created_at"])[:10], center=True))

            rm_btn = QPushButton("Remove")
            rm_btn.setObjectName("ghostBtn")
            rm_btn.clicked.connect(
                lambda _, rid=row["id"]: self._remove_ignore(rid)
            )
            self._ignore_table.setCellWidget(r_i, 3, rm_btn)

    def _remove_ignore(self, ignore_id: int) -> None:
        if self._db:
            self._db.remove_ignore(ignore_id)
            self._load_ignore_list()

    # ── Custom rules section ──────────────────────────────────────────────────

    def _build_rules_section(self) -> QGroupBox:
        box = QGroupBox("⚙️ Custom Keyword Rules")
        layout = QVBoxLayout(box)

        self._rules_table = QTableWidget()
        self._rules_table.setColumnCount(4)
        self._rules_table.setHorizontalHeaderLabels(
            ["Keyword", "Matches In", "Category", "Action"]
        )
        self._rules_table.verticalHeader().setVisible(False)
        hdr = self._rules_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._rules_table.setMaximumHeight(200)
        layout.addWidget(self._rules_table)

        add_btn = QPushButton("+ Add Rule")
        add_btn.setObjectName("ghostBtn")
        add_btn.clicked.connect(self._add_rule)
        layout.addWidget(add_btn)

        return box

    def _load_rules(self) -> None:
        rules = self._config.get("custom_rules", [])
        self._rules_table.setRowCount(len(rules))
        for r_i, rule in enumerate(rules):
            self._rules_table.setItem(r_i, 0, _item(rule.get("keyword", "")))
            self._rules_table.setItem(r_i, 1, _item(rule.get("match_in", "both"), center=True))
            self._rules_table.setItem(r_i, 2, _item(rule.get("category", "Other"), center=True))
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("ghostBtn")
            del_btn.clicked.connect(lambda _, i=r_i: self._delete_rule(i))
            self._rules_table.setCellWidget(r_i, 3, del_btn)

    def _add_rule(self) -> None:
        dlg = _AddRuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rule = dlg.get_rule()
            rules = self._config.setdefault("custom_rules", [])
            rules.append(rule)
            self._save_config()
            self._load_rules()

    def _delete_rule(self, index: int) -> None:
        rules = self._config.get("custom_rules", [])
        if 0 <= index < len(rules):
            rules.pop(index)
            self._save_config()
            self._load_rules()

    # ── AI Backend section ────────────────────────────────────────────────────

    def _build_ai_backend_section(self) -> QGroupBox:
        box = QGroupBox("🤖 Stage 3 AI Backend")
        layout = QVBoxLayout(box)

        desc = QLabel(
            "Controls which AI model handles ambiguous emails after rules + ML stages."
        )
        desc.setObjectName("statusLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._radio_distilbert = QRadioButton(
            "DistilBERT  (faster · CPU-only · ~200 ms/email · no Ollama needed)"
        )
        self._radio_phi4mini = QRadioButton(
            "phi4-mini via Ollama  (zero-shot · better for ambiguous emails · requires Ollama)"
        )
        layout.addWidget(self._radio_distilbert)
        layout.addWidget(self._radio_phi4mini)

        self._radio_distilbert.toggled.connect(self._on_backend_radio_changed)

        return box

    def _load_ai_backend(self) -> None:
        try:
            from classifier.config import _load_stage3_backend
            backend = _load_stage3_backend()
        except Exception:
            backend = "distilbert"
        if backend == "phi4-mini":
            self._radio_phi4mini.setChecked(True)
        else:
            self._radio_distilbert.setChecked(True)

    def _on_backend_radio_changed(self, checked: bool) -> None:
        if not checked:
            return  # handle only the "selected" transition
        backend = "distilbert" if self._radio_distilbert.isChecked() else "phi4-mini"
        try:
            from classifier.config import save_stage3_backend
            save_stage3_backend(backend)
        except Exception as exc:
            logger.error("Could not save Stage 3 backend: %s", exc)
            return

        if backend == "phi4-mini":
            import urllib.request
            try:
                urllib.request.urlopen("http://localhost:11434", timeout=2)
            except Exception:
                QMessageBox.warning(
                    self,
                    "Ollama Not Running",
                    "phi4-mini requires Ollama to be running.\n\n"
                    "Install: https://ollama.com\n"
                    "Start:   ollama serve\n"
                    "Pull:    ollama pull phi4-mini\n\n"
                    "Stage 3 will fall back to REVIEW until Ollama is available.",
                )

        self.backend_changed.emit(backend)

    # ── Data management section ───────────────────────────────────────────────

    def _build_data_section(self) -> QGroupBox:
        box = QGroupBox("🗄️ Data Management")
        layout = QVBoxLayout(box)

        # App data folder
        row1 = QWidget()
        r1l  = QHBoxLayout(row1)
        r1l.setContentsMargins(0, 0, 0, 0)
        self._data_dir_label = QLabel("—")
        self._data_dir_label.setObjectName("statusLabel")
        r1l.addWidget(QLabel("Data folder:"))
        r1l.addWidget(self._data_dir_label, stretch=1)
        change_btn = QPushButton("Change…")
        change_btn.clicked.connect(self._change_data_dir)
        r1l.addWidget(change_btn)
        layout.addWidget(row1)

        # Clear cache
        row2 = QWidget()
        r2l  = QHBoxLayout(row2)
        r2l.setContentsMargins(0, 0, 0, 0)
        r2l.addWidget(QLabel("Clear cache for current month:"))
        clear_btn = QPushButton("Clear Cache")
        clear_btn.clicked.connect(lambda: self.clear_cache_requested.emit(""))
        r2l.addWidget(clear_btn)
        r2l.addStretch()
        layout.addWidget(row2)

        # Re-authenticate
        reauth_btn = QPushButton("🔄 Re-authenticate Gmail")
        reauth_btn.setObjectName("ghostBtn")
        reauth_btn.clicked.connect(self.reauth_requested.emit)
        layout.addWidget(reauth_btn)

        return box

    def _change_data_dir(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        chosen = QFileDialog.getExistingDirectory(self, "Choose Data Directory")
        if chosen:
            path = Path(chosen)
            self.data_dir_changed.emit(path)

    # ── Load all ──────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        if self._data_dir:
            self._data_dir_label.setText(str(self._data_dir))
        self._load_budgets()
        self._load_ignore_list()
        self._load_rules()
        self._load_ai_backend()

    def refresh(self) -> None:
        """Called after a new fetch to refresh budget actuals."""
        self._load_budgets()

    # ── Config persistence ────────────────────────────────────────────────────

    def _save_config(self) -> None:
        if not self._data_dir:
            return
        config_path = self._data_dir / "config.json"
        try:
            config_path.write_text(json.dumps(self._config, indent=2))
        except OSError as exc:
            logger.error("Could not save config.json: %s", exc)

    def get_custom_rules(self) -> list[dict]:
        return self._config.get("custom_rules", [])


# ── Sub-dialogs ───────────────────────────────────────────────────────────────

class _BudgetEditDialog(QDialog):
    def __init__(self, category: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Set Budget — {category}")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Monthly budget for <b>{category}</b>:"))
        self._spin = QDoubleSpinBox()
        self._spin.setRange(0, 9_999_999)
        self._spin.setPrefix("₹ ")
        self._spin.setDecimals(0)
        layout.addWidget(self._spin)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_value(self) -> float:
        return self._spin.value()


class _AddRuleDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Custom Rule")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Keyword:"))
        self._kw = QLineEdit()
        self._kw.setPlaceholderText("e.g. 'grofers' or 'payslip'")
        layout.addWidget(self._kw)

        layout.addWidget(QLabel("Matches in:"))
        self._match_in = QComboBox()
        self._match_in.addItems(["both", "sender", "subject"])
        layout.addWidget(self._match_in)

        layout.addWidget(QLabel("Category:"))
        self._cat = QComboBox()
        for cat in ALL_CATEGORIES:
            self._cat.addItem(cat)
        layout.addWidget(self._cat)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_rule(self) -> dict:
        return {
            "keyword":  self._kw.text().strip().lower(),
            "match_in": self._match_in.currentText(),
            "category": self._cat.currentText(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item(text: str, center: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it
