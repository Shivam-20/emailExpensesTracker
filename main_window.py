"""
main_window.py — QMainWindow: sidebar + 5-tab main area.
Supports single-month, date-range, full-year, and all-available multi-fetch.
"""

import calendar
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
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

        # Multi-fetch state
        self._fetch_queue: list[tuple[int, int]] = []
        self._fetch_accumulated: list[dict] = []
        self._fetch_total: int = 0
        self._fetch_force: bool = False
        self._fetch_label_id: Optional[str] = None

        self.setWindowTitle("💰 Gmail Expense Tracker")
        self.setMinimumSize(1100, 720)
        self._setup_ui()
        self._setup_status_bar()
        self.setStyleSheet(MAIN_STYLE)
        self._post_init()

    # ── UI Construction ───────────────────────────────────────────────────────

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

        # ── Date / Fetch Mode ─────────────────────────────────────────────
        date_label = QLabel("Fetch Mode")
        date_label.setObjectName("sectionLabel")
        lay.addWidget(date_label)
        lay.addSpacing(4)

        self._fetch_mode = QComboBox()
        self._fetch_mode.addItems([
            "Single Month",
            "Month Range",
            "Full Year",
            "All Available",
        ])
        self._fetch_mode.currentIndexChanged.connect(self._on_fetch_mode_changed)
        lay.addWidget(self._fetch_mode)
        lay.addSpacing(4)

        # ── Single month row ──────────────────────────────────────────────
        self._single_row = QWidget()
        single_lay = QHBoxLayout(self._single_row)
        single_lay.setContentsMargins(0, 0, 0, 0)
        single_lay.setSpacing(4)

        self._year_combo = QComboBox()
        for y in range(_NOW_YEAR - 4, _NOW_YEAR + 2):
            self._year_combo.addItem(str(y), y)
        self._year_combo.setCurrentText(str(_NOW_YEAR))

        self._month_combo = QComboBox()
        for i, name in enumerate(calendar.month_name[1:], start=1):
            self._month_combo.addItem(name, i)
        self._month_combo.setCurrentIndex(_NOW_MONTH - 1)

        single_lay.addWidget(self._year_combo)
        single_lay.addWidget(self._month_combo)
        lay.addWidget(self._single_row)

        # ── Month range row ───────────────────────────────────────────────
        self._range_row = QWidget()
        range_lay = QVBoxLayout(self._range_row)
        range_lay.setContentsMargins(0, 0, 0, 0)
        range_lay.setSpacing(2)

        from_row = QWidget()
        from_lay = QHBoxLayout(from_row)
        from_lay.setContentsMargins(0, 0, 0, 0)
        from_lay.setSpacing(4)
        from_lay.addWidget(QLabel("From:"))
        self._from_year = QComboBox()
        for y in range(_NOW_YEAR - 4, _NOW_YEAR + 2):
            self._from_year.addItem(str(y), y)
        self._from_year.setCurrentText(str(_NOW_YEAR - 1))
        self._from_month = QComboBox()
        for i, name in enumerate(calendar.month_abbr[1:], start=1):
            self._from_month.addItem(name, i)
        self._from_month.setCurrentIndex(0)
        from_lay.addWidget(self._from_year)
        from_lay.addWidget(self._from_month)
        range_lay.addWidget(from_row)

        to_row = QWidget()
        to_lay = QHBoxLayout(to_row)
        to_lay.setContentsMargins(0, 0, 0, 0)
        to_lay.setSpacing(4)
        to_lay.addWidget(QLabel("To:  "))
        self._to_year = QComboBox()
        for y in range(_NOW_YEAR - 4, _NOW_YEAR + 2):
            self._to_year.addItem(str(y), y)
        self._to_year.setCurrentText(str(_NOW_YEAR))
        self._to_month = QComboBox()
        for i, name in enumerate(calendar.month_abbr[1:], start=1):
            self._to_month.addItem(name, i)
        self._to_month.setCurrentIndex(_NOW_MONTH - 1)
        to_lay.addWidget(self._to_year)
        to_lay.addWidget(self._to_month)
        range_lay.addWidget(to_row)

        self._range_row.setVisible(False)
        lay.addWidget(self._range_row)

        # ── Full year row ─────────────────────────────────────────────────
        self._year_only_row = QWidget()
        year_only_lay = QHBoxLayout(self._year_only_row)
        year_only_lay.setContentsMargins(0, 0, 0, 0)
        self._year_only_combo = QComboBox()
        for y in range(_NOW_YEAR - 4, _NOW_YEAR + 2):
            self._year_only_combo.addItem(str(y), y)
        self._year_only_combo.setCurrentText(str(_NOW_YEAR))
        year_only_lay.addWidget(self._year_only_combo)
        self._year_only_row.setVisible(False)
        lay.addWidget(self._year_only_row)

        # ── Gmail label filter ────────────────────────────────────────────
        self._label_combo = QComboBox()
        self._label_combo.addItem("All Mail", None)
        lay.addWidget(self._label_combo)

        # Last fetched
        self._last_fetched_lbl = QLabel("Last fetched: —")
        self._last_fetched_lbl.setObjectName("statusLabel")
        self._last_fetched_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._last_fetched_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        lay.addWidget(self._last_fetched_lbl)

        lay.addSpacing(10)

        # ── Actions ───────────────────────────────────────────────────────
        actions_label = QLabel("Actions")
        actions_label.setObjectName("sectionLabel")
        lay.addWidget(actions_label)
        lay.addSpacing(4)

        self._fetch_btn = QPushButton("🔍 Fetch Expenses")
        self._fetch_btn.setObjectName("primaryBtn")
        self._fetch_btn.setToolTip("Fetch expenses (Alt+F)")
        self._fetch_btn.clicked.connect(lambda: self._on_fetch(force=False))
        lay.addWidget(self._fetch_btn)

        self._refresh_btn = QPushButton("🔄 Refresh Cache")
        self._refresh_btn.setObjectName("ghostBtn")
        self._refresh_btn.setToolTip("Force re-fetch from Gmail (bypasses cache)")
        self._refresh_btn.clicked.connect(lambda: self._on_fetch(force=True))
        lay.addWidget(self._refresh_btn)

        lay.addSpacing(12)

        # ── Summary ───────────────────────────────────────────────────────
        summary_label = QLabel("Summary")
        summary_label.setObjectName("sectionLabel")
        lay.addWidget(summary_label)
        lay.addSpacing(4)

        self._summary_card = _SummaryCard()
        lay.addWidget(self._summary_card)

        lay.addSpacing(12)

        # Stage 3 indicator
        self._stage3_lbl = QLabel()
        self._stage3_lbl.setObjectName("statusLabel")
        self._stage3_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._stage3_lbl)

        # Keyboard shortcut hint
        hint = QLabel("Alt+1–5: switch tabs  •  Alt+F: fetch")
        hint.setObjectName("statusLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        lay.addWidget(hint)

        lay.addStretch()
        return sb

    def _on_fetch_mode_changed(self, _idx: int) -> None:
        mode = self._fetch_mode.currentText()
        self._single_row.setVisible(mode == "Single Month")
        self._range_row.setVisible(mode == "Month Range")
        self._year_only_row.setVisible(mode == "Full Year")

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
        self._tabs.addTab(self._expenses_tab, "📋 Expenses")
        self._tabs.addTab(self._charts_tab,   "📊 Charts")
        self._tabs.addTab(self._trends_tab,   "📈 Trends")
        self._tabs.addTab(self._review_tab,   "🔍 Review Queue")
        self._tabs.addTab(self._settings_tab, "⚙️ Settings")
        self._expenses_tab.field_changed.connect(self._on_field_changed)
        self._expenses_tab.exclude_requested.connect(self._on_exclude_requested)
        self._expenses_tab.review_requested.connect(self._on_review_requested)
        self._review_tab.correction_saved.connect(self._on_review_correction)
        self._settings_tab.reauth_requested.connect(self._on_reauth)
        self._settings_tab.clear_cache_requested.connect(self._on_clear_cache)
        self._settings_tab.data_dir_changed.connect(self._on_data_dir_changed)
        self._settings_tab.backend_changed.connect(self._on_backend_changed)
        self._settings_tab.training_finished.connect(self._on_training_finished)
        self._charts_tab.category_drill.connect(self._on_chart_category_drill)
        lay.addWidget(self._tabs)
        return area

    def _setup_status_bar(self) -> None:
        self._sb = QStatusBar()
        self.setStatusBar(self._sb)

        # Cancel button (hidden by default)
        self._cancel_btn = QPushButton("✕ Cancel")
        self._cancel_btn.setObjectName("ghostBtn")
        self._cancel_btn.setFixedWidth(80)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel_fetch)
        self._sb.addPermanentWidget(self._cancel_btn)

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

    # ── Fetch orchestration ───────────────────────────────────────────────────

    def _build_fetch_months(self) -> list[tuple[int, int]]:
        """Return list of (year, month) tuples to fetch based on current mode."""
        mode = self._fetch_mode.currentText()

        if mode == "Single Month":
            return [(self._year_combo.currentData(), self._month_combo.currentData())]

        elif mode == "Full Year":
            year = self._year_only_combo.currentData()
            return [(year, m) for m in range(1, 13)]

        elif mode == "Month Range":
            fy = self._from_year.currentData()
            fm = self._from_month.currentData()
            ty = self._to_year.currentData()
            tm = self._to_month.currentData()
            # Swap if from > to
            if (fy, fm) > (ty, tm):
                fy, fm, ty, tm = ty, tm, fy, fm
            months: list[tuple[int, int]] = []
            y, m = fy, fm
            while (y, m) <= (ty, tm):
                months.append((y, m))
                m += 1
                if m > 12:
                    m = 1; y += 1
                if len(months) > 60:   # safety cap: max 5 years
                    break
            return months

        else:  # All Available
            try:
                available = self._db.get_available_months()
                return [(int(s[:4]), int(s[5:7])) for s in available] if available else \
                       [(_NOW_YEAR, _NOW_MONTH)]
            except Exception:
                return [(_NOW_YEAR, _NOW_MONTH)]

    def _on_fetch(self, force: bool = False) -> None:
        if not CREDENTIALS_PATH.exists():
            QMessageBox.warning(self, "Missing credentials.json",
                                "Place credentials.json in the app directory.")
            return
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(2000)

        months = self._build_fetch_months()
        if not months:
            return

        self._fetch_queue       = list(months)
        self._fetch_accumulated = []
        self._fetch_total       = len(months)
        self._fetch_force       = force
        self._fetch_label_id    = self._label_combo.currentData()

        self._fetch_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._expenses_tab.clear()
        self._charts_tab.clear()

        self._start_next_fetch()

    def _start_next_fetch(self) -> None:
        if not self._fetch_queue:
            self._on_all_fetches_complete()
            return

        year, month = self._fetch_queue.pop(0)
        done = self._fetch_total - len(self._fetch_queue) - 1
        self._sb.showMessage(
            f"Fetching {calendar.month_name[month]} {year}…"
            + (f" ({done + 1}/{self._fetch_total})" if self._fetch_total > 1 else "")
        )
        rules = self._settings_tab.get_custom_rules()
        self._worker = GmailWorker(
            data_dir=self.data_dir, year=year, month=month,
            label_id=self._fetch_label_id, force_refresh=self._fetch_force,
            custom_rules=rules, parent=self,
        )
        self._worker.progress.connect(self._on_month_progress)
        self._worker.status.connect(self._sb.showMessage)
        self._worker.authenticated.connect(self._on_authenticated)
        self._worker.labels_ready.connect(self._on_labels_ready)
        self._worker.finished.connect(self._on_month_fetch_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_month_progress(self, current: int, total: int) -> None:
        done = self._fetch_total - len(self._fetch_queue) - 1
        base_pct = done / self._fetch_total * 100
        if total > 0:
            month_pct = current / total * (100 / self._fetch_total)
        else:
            month_pct = 100 / self._fetch_total
        self._progress.setValue(int(base_pct + month_pct))

    def _on_month_fetch_finished(self, rows: list) -> None:
        self._fetch_accumulated.extend(rows)
        done = self._fetch_total - len(self._fetch_queue)
        self._progress.setValue(int(done / self._fetch_total * 100))
        self._start_next_fetch()

    def _on_all_fetches_complete(self) -> None:
        rows = self._fetch_accumulated
        self._current_rows = rows

        # Determine chart year/month: most recent fetched month
        now = datetime.now()
        chart_year, chart_month = now.year, now.month

        # Compute previous-month total for MoM delta (single-month only)
        prev_total: Optional[float] = None
        if self._fetch_total == 1 and self._fetch_mode.currentText() == "Single Month":
            chart_year  = self._year_combo.currentData()
            chart_month = self._month_combo.currentData()
            prev_total  = self._compute_prev_month_total(chart_year, chart_month)

        self._expenses_tab.set_db(self._db)
        self._expenses_tab.load_rows(rows)
        self._charts_tab.update_charts(rows, chart_year, chart_month, prev_total)
        self._settings_tab.refresh()
        self._review_tab.refresh()
        self._update_review_badge()
        self._fetch_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._update_summary_card(rows, prev_total)

        # Update last-fetched timestamp
        self._last_fetched_lbl.setText(
            f"Last fetched: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        self._last_fetched_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 11px;")

        if not rows:
            n = self._fetch_total
            label = "the selected period" if n > 1 else \
                    f"{calendar.month_name[self._month_combo.currentData()]} {self._year_combo.currentData()}"
            QMessageBox.information(self, "No Expenses Found",
                                    f"No expense emails found for {label}.")

    def _on_cancel_fetch(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
        self._fetch_queue = []
        self._fetch_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._sb.showMessage("Fetch cancelled.")

    def _compute_prev_month_total(self, year: int, month: int) -> Optional[float]:
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        try:
            rows = self._db.get_month_expenses(f"{prev_y}-{prev_m:02d}")
            if not rows:
                return None
            return sum(
                (r.get("amount_edited") or r.get("amount") or 0)
                for r in rows if r.get("status") != "excluded"
            )
        except Exception:
            return None

    # ── Auth ──────────────────────────────────────────────────────────────────

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

    # ── Field change (with real-time chart refresh) ───────────────────────────

    def _on_field_changed(self, msg_id: str, field: str, value) -> None:
        try:
            self._db.update_expense_field(msg_id, field, value)
        except Exception as exc:
            logger.error("Persist failed %s/%s: %s", msg_id, field, exc)

        # When status → review, also set needs_review flag
        if field == "status" and value == "review":
            try:
                self._db.conn.execute(
                    "UPDATE expenses SET needs_review = 1 WHERE id = ?", (msg_id,)
                )
                self._db.conn.commit()
            except Exception as exc:
                logger.error("Could not set needs_review: %s", exc)

        # Update in-memory copy for chart refresh
        for r in self._current_rows:
            if r.get("id") == msg_id:
                r[field] = value
                break

        # Real-time chart + summary refresh on data changes
        if field in ("amount_edited", "category_edited", "status"):
            y = self._year_combo.currentData() if self._fetch_mode.currentText() == "Single Month" \
                else datetime.now().year
            m = self._month_combo.currentData() if self._fetch_mode.currentText() == "Single Month" \
                else datetime.now().month
            self._charts_tab.update_charts(self._current_rows, y, m)
            self._update_summary_card(self._current_rows)

        if field == "status":
            self._review_tab.refresh()
            self._update_review_badge()

    def _update_summary_card(self, rows: list, prev_total: Optional[float] = None) -> None:
        active = [r for r in rows if r.get("status") != "excluded"]
        if not active:
            self._summary_card.update("—", "—", "—", "")
            return
        total = sum(r.get("amount_edited") or r.get("amount") or 0 for r in active)
        cat_totals: dict[str, float] = defaultdict(float)
        for r in active:
            cat = r.get("category_edited") or r.get("category", "Other")
            cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cat = max(cat_totals, key=lambda c: cat_totals[c]) if cat_totals else "—"

        delta_str = ""
        if prev_total and prev_total > 0:
            delta_pct = (total - prev_total) / prev_total * 100
            arrow = "↑" if delta_pct >= 0 else "↓"
            delta_str = f"{arrow}{abs(delta_pct):.1f}% vs prev"

        self._summary_card.update(f"₹{total:,.0f}", f"{len(active)} txns", top_cat, delta_str)

    # ── Worker errors ─────────────────────────────────────────────────────────

    def _on_worker_error(self, msg: str) -> None:
        self._fetch_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._sb.showMessage("❌ Error")
        QMessageBox.critical(self, "Error", msg)

    # ── Tab signal handlers ───────────────────────────────────────────────────

    def _on_exclude_requested(self, msg_id: str, sender_email: str) -> None:
        reply = QMessageBox.question(
            self, "Add to Ignore List?",
            f"Also ignore future emails from {sender_email}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.add_ignore("sender", sender_email)
            self._settings_tab._load_ignore_list()

    def _on_review_requested(self, msg_id: str) -> None:
        if self._db:
            try:
                self._db.conn.execute(
                    "UPDATE expenses SET needs_review = 1 WHERE id = ?", (msg_id,)
                )
                self._db.conn.commit()
            except Exception as exc:
                logger.error("Could not mark for review: %s", exc)
        self._review_tab.refresh()
        self._update_review_badge()

    def _on_review_correction(self, msg_id: str, new_label: str) -> None:
        self._update_review_badge()

    def _on_training_finished(self, success: bool, message: str) -> None:
        if success:
            self._sb.showMessage("✅ Model training completed.", 5000)
        else:
            self._sb.showMessage(f"❌ Training failed: {message}", 8000)

    def _on_chart_category_drill(self, category: str) -> None:
        """When user clicks a chart segment, filter the Expenses tab to that category."""
        self._tabs.setCurrentWidget(self._expenses_tab)
        self._expenses_tab.filter_by_category(category)

    # ── Review badge ──────────────────────────────────────────────────────────

    def _update_review_badge(self) -> None:
        count = self._review_tab.get_review_count()
        review_idx = self._tabs.indexOf(self._review_tab)
        if count > 0:
            badge_color = ERROR if count > 10 else WARNING if count > 5 else ACCENT
            badge = (f" 🔍 <span style='background-color: {badge_color}; "
                     f"color: {BG}; padding: 2px 8px; border-radius: 12px; "
                     f"font-size: 11px; font-weight: 600;'>{count}</span>")
            self._tabs.setTabText(review_idx, f"Review Queue{badge}")
        else:
            self._tabs.setTabText(review_idx, "🔍 Review Queue")

    # ── Settings handlers ─────────────────────────────────────────────────────

    def _on_reauth(self) -> None:
        revoke_credentials(self.data_dir)
        self._account_pill.setText("Not connected")
        self._connect_btn.setVisible(True)
        QMessageBox.information(self, "Re-authenticate",
                                "Cleared. Click Connect Gmail to log in again.")

    def _on_clear_cache(self, month_str: str) -> None:
        if not month_str:
            if self._fetch_mode.currentText() == "Single Month":
                year  = self._year_combo.currentData()
                month = self._month_combo.currentData()
                month_str = f"{year}-{month:02d}"
            else:
                month_str = f"{_NOW_YEAR}-{_NOW_MONTH:02d}"
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

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _setup_tab_shortcuts(self) -> None:
        for key_seq, index in [
            (QKeySequence("Alt+1"), 0),
            (QKeySequence("Alt+2"), 1),
            (QKeySequence("Alt+3"), 2),
            (QKeySequence("Alt+4"), 3),
            (QKeySequence("Alt+5"), 4),
        ]:
            sc = QShortcut(key_seq, self)
            sc.activated.connect(lambda i=index: self._tabs.setCurrentIndex(i))

        fetch_sc = QShortcut(QKeySequence("Alt+F"), self)
        fetch_sc.activated.connect(
            lambda: self._fetch_btn.click() if self._fetch_btn.isEnabled() else None
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(3000)
        self._db.close()
        event.accept()


# ── Summary card ──────────────────────────────────────────────────────────────

class _SummaryCard(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        lay.setSpacing(4)

        top_row = QWidget()
        top_lay = QHBoxLayout(top_row)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(SPACING_LG)

        self._total_lbl = QLabel("—")
        self._total_lbl.setObjectName("summaryValue")
        self._count_lbl = QLabel("—")
        self._count_lbl.setObjectName("summaryValue")
        self._cat_lbl   = QLabel("—")
        self._cat_lbl.setObjectName("summaryValue")

        top_lay.addWidget(self._total_lbl, stretch=1)
        top_lay.addWidget(self._count_lbl, stretch=1)
        top_lay.addWidget(self._cat_lbl,   stretch=1)
        lay.addWidget(top_row)

        self._delta_lbl = QLabel("")
        self._delta_lbl.setObjectName("statusLabel")
        self._delta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._delta_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM};")
        self._delta_lbl.setVisible(False)
        lay.addWidget(self._delta_lbl)

    def update(self, total: str, count: str, top_cat: str, delta: str = "") -> None:
        self._total_lbl.setText(f"💰 {total}")
        self._count_lbl.setText(f"📦 {count}")
        self._cat_lbl.setText(f"🏆 {top_cat}")
        if delta:
            color = WARNING if delta.startswith("↑") else SUCCESS
            self._delta_lbl.setText(delta)
            self._delta_lbl.setStyleSheet(f"font-size: 11px; color: {color};")
            self._delta_lbl.setVisible(True)
        else:
            self._delta_lbl.setVisible(False)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
