"""
main_window.py — QMainWindow: sidebar + 4-tab main area.
Wires sidebar controls to GmailWorker and all tabs.
"""

import calendar
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSizePolicy,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from tabs.expenses_tab      import ExpensesTab
from tabs.charts_tab        import ChartsTab
from tabs.trends_tab        import TrendsTab
from tabs.review_queue_tab  import ReviewQueueTab
from tabs.settings_tab      import SettingsTab
from tabs.training_tab      import TrainingTab
from workers.gmail_worker import GmailWorker, AuthOnlyWorker
from core.db import Database
from core.gmail_auth import is_authenticated, CREDENTIALS_PATH, revoke_credentials
from styles import (
    ACCENT, BG, BORDER, SIDEBAR_BG, SURFACE, TEXT, TEXT_DIM, SUCCESS, WARNING, ERROR, MAIN_STYLE,
    SPACING_SM, SPACING_MD, SPACING_LG, RADIUS_SM, RADIUS_MD,
)

logger = logging.getLogger(__name__)

_NOW_YEAR  = datetime.now().year
_NOW_MONTH = datetime.now().month


class MainWindow(QMainWindow):
    def __init__(self, data_dir: Path) -> None:
        super().__init__()
        self.data_dir = data_dir
        self._worker: Optional[GmailWorker] = None
        self._labels: list[dict] = []
        self._current_rows: list[dict] = []
        self._config = _load_config(data_dir)
        self._db = Database(data_dir)
        self._db.connect()

        self.setWindowTitle("💰 Gmail Expense Tracker")
        self.setMinimumSize(1100, 720)
        self._setup_ui()
        self._setup_status_bar()
        self.setStyleSheet(MAIN_STYLE)
        self._post_init()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar(), stretch=0)
        root.addWidget(self._build_main_area(), stretch=1)

    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(280)
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(0)

        title = QLabel("💰 Expense Tracker")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addSpacing(8)

        self._account_pill = QLabel("Not connected")
        self._account_pill.setObjectName("accountPill")
        self._account_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._account_pill.setWordWrap(True)
        lay.addWidget(self._account_pill)

        self._connect_btn = QPushButton("🔑 Connect Gmail")
        self._connect_btn.setObjectName("ghostBtn")
        self._connect_btn.clicked.connect(self._on_connect)
        lay.addWidget(self._connect_btn)

        lay.addWidget(_sep())
        lay.addSpacing(8)

        year_month_label = QLabel("Date Selection")
        year_month_label.setObjectName("sectionLabel")
        lay.addWidget(year_month_label)
        lay.addSpacing(4)

        self._year_combo = QComboBox()
        for y in range(_NOW_YEAR - 3, _NOW_YEAR + 4):
            self._year_combo.addItem(str(y), y)
        self._year_combo.setCurrentText(str(_NOW_YEAR))
        lay.addWidget(self._year_combo)

        self._month_combo = QComboBox()
        for i, name in enumerate(calendar.month_name[1:], start=1):
            self._month_combo.addItem(name, i)
        self._month_combo.setCurrentIndex(_NOW_MONTH - 1)
        lay.addWidget(self._month_combo)

        self._label_combo = QComboBox()
        self._label_combo.addItem("All Mail", None)
        lay.addWidget(self._label_combo)

        lay.addSpacing(12)

        actions_label = QLabel("Actions")
        actions_label.setObjectName("sectionLabel")
        lay.addWidget(actions_label)
        lay.addSpacing(4)

        self._fetch_btn = QPushButton("🔍 Fetch Expenses")
        self._fetch_btn.setObjectName("primaryBtn")
        self._fetch_btn.setToolTip("Fetch expenses from Gmail")
        self._fetch_btn.clicked.connect(lambda: self._on_fetch(force=False))
        lay.addWidget(self._fetch_btn)

        self._refresh_btn = QPushButton("🔄 Refresh Cache")
        self._refresh_btn.setObjectName("ghostBtn")
        self._refresh_btn.setToolTip("Force refresh from server")
        self._refresh_btn.clicked.connect(lambda: self._on_fetch(force=True))
        lay.addWidget(self._refresh_btn)

        lay.addSpacing(12)

        summary_label = QLabel("Summary")
        summary_label.setObjectName("sectionLabel")
        lay.addWidget(summary_label)
        lay.addSpacing(4)

        self._summary_card = _SummaryCard()
        lay.addWidget(self._summary_card)

        lay.addSpacing(12)

        self._stage3_lbl = QLabel()
        self._stage3_lbl.setObjectName("statusLabel")
        self._stage3_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._stage3_lbl)

        lay.addStretch()
        return sb

    def _build_main_area(self) -> QWidget:
        area = QWidget()
        lay  = QVBoxLayout(area)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._tabs = QTabWidget()
        self._expenses_tab    = ExpensesTab(db=self._db)
        self._charts_tab      = ChartsTab()
        self._trends_tab      = TrendsTab()
        self._review_tab      = ReviewQueueTab()
        self._settings_tab    = SettingsTab()
        self._training_tab    = TrainingTab()
        self._tabs.addTab(self._expenses_tab, "📋 Expenses")
        self._tabs.addTab(self._charts_tab,   "📊 Charts")
        self._tabs.addTab(self._trends_tab,   "📈 Trends")
        self._tabs.addTab(self._review_tab,   "🔍 Review Queue")
        self._tabs.addTab(self._training_tab, "🧠 Training")
        self._tabs.addTab(self._settings_tab, "⚙️ Settings")
        self._expenses_tab.field_changed.connect(self._on_field_changed)
        self._expenses_tab.exclude_requested.connect(self._on_exclude_requested)
        self._review_tab.correction_saved.connect(self._on_review_correction)
        self._settings_tab.reauth_requested.connect(self._on_reauth)
        self._settings_tab.clear_cache_requested.connect(self._on_clear_cache)
        self._settings_tab.data_dir_changed.connect(self._on_data_dir_changed)
        self._settings_tab.backend_changed.connect(self._on_backend_changed)
        lay.addWidget(self._tabs)
        return area

    def _setup_status_bar(self) -> None:
        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._progress = QProgressBar()
        self._progress.setFixedWidth(220)
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._sb.addPermanentWidget(self._progress)
        self._sb.showMessage("Ready")

    def _post_init(self) -> None:
        self._settings_tab.set_db(self._db, self.data_dir, self._config)
        self._trends_tab.set_db(self._db, self.data_dir)
        self._review_tab.set_db(self._db, self.data_dir)
        self._training_tab.set_data_dir(self.data_dir, self._db.db_path)
        self._update_stage3_label()
        self._update_review_badge()
        self._setup_tab_shortcuts()
        if not CREDENTIALS_PATH.exists():
            self._account_pill.setText("⚠ credentials.json missing")
            return
        if is_authenticated(self.data_dir):
            worker = AuthOnlyWorker(self.data_dir, parent=self)
            worker.authenticated.connect(self._on_authenticated)
            worker.labels_ready.connect(self._on_labels_ready)
            worker.error.connect(lambda msg: logger.warning("Auth-only: %s", msg))
            worker.start()

    def _on_connect(self) -> None:
        if not CREDENTIALS_PATH.exists():
            QMessageBox.warning(self, "Missing credentials.json",
                                f"Place credentials.json in:\n{CREDENTIALS_PATH}")
            return
        self._account_pill.setText("Connecting…")
        worker = AuthOnlyWorker(self.data_dir, parent=self)
        worker.authenticated.connect(self._on_authenticated)
        worker.labels_ready.connect(self._on_labels_ready)
        worker.error.connect(self._on_worker_error)
        worker.start()
        self._worker = worker

    def _on_authenticated(self, email: str) -> None:
        self._account_pill.setText(f"● {email}")
        self._account_pill.setProperty("connected", True)
        self._account_pill.style().unpolish(self._account_pill)
        self._account_pill.style().polish(self._account_pill)
        self._connect_btn.setVisible(False)
        self._sb.showMessage(f"Connected as {email}")

    def _on_labels_ready(self, labels: list) -> None:
        self._labels = labels
        self._label_combo.clear()
        self._label_combo.addItem("All Mail", None)
        for lbl in labels:
            self._label_combo.addItem(lbl["name"], lbl["id"])

    def _on_fetch(self, force: bool = False) -> None:
        if not CREDENTIALS_PATH.exists():
            QMessageBox.warning(self, "Missing credentials.json", "Place credentials.json in the app directory.")
            return
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(2000)
        year     = self._year_combo.currentData()
        month    = self._month_combo.currentData()
        label_id = self._label_combo.currentData()
        rules    = self._settings_tab.get_custom_rules()
        self._fetch_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._expenses_tab.clear()
        self._charts_tab.clear()
        self._worker = GmailWorker(
            data_dir=self.data_dir, year=year, month=month,
            label_id=label_id, force_refresh=force,
            custom_rules=rules, parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._sb.showMessage)
        self._worker.authenticated.connect(self._on_authenticated)
        self._worker.labels_ready.connect(self._on_labels_ready)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)

    def _on_fetch_finished(self, rows: list) -> None:
        self._current_rows = rows
        year  = self._year_combo.currentData()
        month = self._month_combo.currentData()
        self._expenses_tab.set_db(self._db)
        self._expenses_tab.load_rows(rows)
        self._charts_tab.update_charts(rows, year, month)
        self._settings_tab.refresh()
        self._review_tab.refresh()
        self._update_review_badge()
        self._fetch_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._update_summary_card(rows)
        if not rows:
            QMessageBox.information(self, "No Expenses Found",
                f"No expense emails found for {calendar.month_name[month]} {year}.")

    def _update_summary_card(self, rows: list) -> None:
        active = [r for r in rows if r.get("status") != "excluded"]
        if not active:
            self._summary_card.update("—", "—", "—")
            return
        total = sum(r.get("amount_edited") or r.get("amount") or 0 for r in active)
        cat_totals: dict[str, float] = defaultdict(float)
        for r in active:
            cat = r.get("category_edited") or r.get("category", "Other")
            cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cat = max(cat_totals, key=lambda c: cat_totals[c]) if cat_totals else "—"
        self._summary_card.update(f"₹{total:,.0f}", f"{len(active)} txns", top_cat)

    def _on_worker_error(self, msg: str) -> None:
        self._fetch_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._sb.showMessage("❌ Error")
        QMessageBox.critical(self, "Error", msg)

    def _on_field_changed(self, msg_id: str, field: str, value) -> None:
        try:
            self._db.update_expense_field(msg_id, field, value)
        except Exception as exc:
            logger.error("Persist failed %s/%s: %s", msg_id, field, exc)

    def _on_exclude_requested(self, msg_id: str, sender_email: str) -> None:
        reply = QMessageBox.question(
            self, "Add to Ignore List?",
            f"Also ignore future emails from {sender_email}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.add_ignore("sender", sender_email)
            self._settings_tab._load_ignore_list()

    def _on_reauth(self) -> None:
        revoke_credentials(self.data_dir)
        self._account_pill.setText("Not connected")
        self._connect_btn.setVisible(True)
        QMessageBox.information(self, "Re-authenticate", "Cleared. Click Connect Gmail to log in again.")

    def _on_clear_cache(self, month_str: str) -> None:
        if not month_str:
            year  = self._year_combo.currentData()
            month = self._month_combo.currentData()
            month_str = f"{year}-{month:02d}"
        reply = QMessageBox.question(self, "Clear Cache",
            f"Delete cached expenses for {month_str}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_month(month_str)
            self._expenses_tab.clear()
            self._charts_tab.clear()
            self._sb.showMessage(f"Cache cleared for {month_str}.")

    def _on_data_dir_changed(self, new_path: Path) -> None:
        QMessageBox.information(self, "Restart Required",
            f"Data directory will change to:\n{new_path}\n\nRestart the app to apply.")
        _save_bootstrap_path(new_path)

    def _on_review_correction(self, msg_id: str, new_label: str) -> None:
        self._update_review_badge()

    def _update_review_badge(self) -> None:
        """Update the Review Queue tab label with a count badge."""
        count = self._review_tab.get_review_count()
        review_idx = self._tabs.indexOf(self._review_tab)
        
        if count > 0:
            if count > 10:
                badge_color = ERROR
            elif count > 5:
                badge_color = WARNING
            else:
                badge_color = ACCENT
                
            badge = f" 🔍 <span style='background-color: {badge_color}; "
            badge += f"color: {BG}; padding: 2px 8px; border-radius: 12px; "
            badge += f"font-size: 11px; font-weight: 600;'>{count}</span>"
            self._tabs.setTabText(review_idx, f"Review Queue{badge}")
        else:
            self._tabs.setTabText(review_idx, "🔍 Review Queue")

    def _on_backend_changed(self, backend: str) -> None:
        self._update_stage3_label()

    def _update_stage3_label(self) -> None:
        try:
            from classifier.config import _load_stage3_backend
            backend = _load_stage3_backend()
        except Exception:
            backend = "distilbert"

        if backend == "phi4-mini":
            ollama_ok = self._check_ollama()
            if ollama_ok:
                self._stage3_lbl.setText("🦙 Stage 3: phi4-mini ✅")
                self._stage3_lbl.setStyleSheet(f"color: {SUCCESS};")
            else:
                self._stage3_lbl.setText("🦙 Stage 3: phi4-mini ⚠️")
                self._stage3_lbl.setStyleSheet(f"color: {WARNING};")
        else:
            self._stage3_lbl.setText("🧠 Stage 3: DistilBERT")
            self._stage3_lbl.setStyleSheet(f"color: {TEXT_DIM};")

    def _check_ollama(self) -> bool:
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434", timeout=2)
            return True
        except Exception:
            return False

    def _setup_tab_shortcuts(self) -> None:
        """Setup keyboard shortcuts for tab navigation."""
        shortcuts = [
            (QKeySequence("Alt+1"), 0),
            (QKeySequence("Alt+2"), 1),
            (QKeySequence("Alt+3"), 2),
            (QKeySequence("Alt+4"), 3),
            (QKeySequence("Alt+5"), 4),
            (QKeySequence("Alt+6"), 5),
        ]
        for key_seq, index in shortcuts:
            shortcut = self.create_shortcut(key_seq, self, lambda _checked, i=index: self._tabs.setCurrentIndex(i))

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(3000)
        self._db.close()
        event.accept()


class _SummaryCard(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryCard")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        lay.setSpacing(SPACING_LG)
        
        self._total_lbl = QLabel("—")
        self._total_lbl.setObjectName("summaryValue")
        self._total_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self._count_lbl = QLabel("—")
        self._count_lbl.setObjectName("summaryValue")
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._cat_lbl = QLabel("—")
        self._cat_lbl.setObjectName("summaryValue")
        self._cat_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        lay.addWidget(self._total_lbl, stretch=1)
        lay.addWidget(self._count_lbl, stretch=1)
        lay.addWidget(self._cat_lbl, stretch=1)
    
    def update(self, total: str, count: str, top_cat: str) -> None:
        self._total_lbl.setText(f"💰 {total}")
        self._count_lbl.setText(f"📦 {count}")
        self._cat_lbl.setText(f"🏆 {top_cat}")


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setObjectName("separator")
    return line


def _load_config(data_dir: Path) -> dict:
    config_path = data_dir / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            pass
    return {"custom_rules": []}


def _save_bootstrap_path(path: Path) -> None:
    bootstrap = Path.home() / ".expense-tracker-path"
    try:
        bootstrap.write_text(str(path))
    except OSError as exc:
        logger.error("Could not save bootstrap: %s", exc)
