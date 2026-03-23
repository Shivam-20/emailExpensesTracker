"""
tabs/expenses_tab.py — Full expense table with toolbar, category chips,
amount filter, bulk actions, context menu, and inline editing.
"""

import json
import logging
from typing import Optional

from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDateEdit, QDialog, QDialogButtonBox,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QComboBox,
)

from config.category_map import ALL_CATEGORIES
from styles import (
    CATEGORY_COLORS, CONFIDENCE_COLORS, CONFIDENCE_BADGES,
    TEXT, TEXT_DIM, SURFACE, SURFACE2, SURFACE3, SURFACE_HOVER,
    ACCENT, ACCENT_DK, WARNING, ERROR, SUCCESS, AMBER, BORDER,
)

logger = logging.getLogger(__name__)

COLUMNS = [
    "✓", "Date", "Sender", "Subject", "Amount",
    "Currency", "Payment", "Category", "Tags", "Confidence", "Status"
]
CI = {name: i for i, name in enumerate(COLUMNS)}


class ExpensesTab(QWidget):
    """Tab 1 — Expense table with all v2 features."""

    # Emitted when user edits a row field (for DB persistence)
    field_changed     = pyqtSignal(str, str, object)   # (msg_id, field, value)
    exclude_requested = pyqtSignal(str, str)            # (msg_id, sender_email)
    review_requested  = pyqtSignal(str)                 # (msg_id,) → mark for review

    def __init__(self, db=None, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._all_rows: list[dict] = []
        self._visible_rows: list[dict] = []
        self._active_categories: set[str] = set()  # empty = all
        self._chip_btns: dict[str, QPushButton] = {}
        self._setup_ui()

    def set_db(self, db) -> None:
        self._db = db

    # ── Public API ────────────────────────────────────────────────────────────

    def load_rows(self, rows: list[dict]) -> None:
        self._all_rows = rows
        self._active_categories.clear()
        self._update_all_chip_state()
        self._apply_filters()

    def get_visible_rows(self) -> list[dict]:
        return list(self._visible_rows)

    def clear(self) -> None:
        self._all_rows = []
        self._visible_rows = []
        self._table.setRowCount(0)
        self._update_summary_label()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = QWidget()
        tb_layout = QVBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search sender, subject, category, tag…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filters)
        tb_layout.addWidget(self._search)

        # Category chips row
        chips_scroll = QScrollArea()
        chips_scroll.setFrameShape(QFrame.Shape.NoFrame)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setFixedHeight(36)
        chips_scroll.setWidgetResizable(True)

        chips_widget = QWidget()
        chips_layout = QHBoxLayout(chips_widget)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(4)

        all_chip = QPushButton("All")
        all_chip.setObjectName("chipActive")
        all_chip.setCheckable(True)
        all_chip.setChecked(True)
        all_chip.clicked.connect(lambda: self._on_all_chip())
        chips_layout.addWidget(all_chip)
        self._chip_btns["All"] = all_chip

        for cat in ALL_CATEGORIES:
            btn = QPushButton(cat)
            btn.setObjectName("chipInactive")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cat: self._on_chip_toggled(c, checked))
            chips_layout.addWidget(btn)
            self._chip_btns[cat] = btn

        chips_layout.addStretch()
        chips_scroll.setWidget(chips_widget)
        tb_layout.addWidget(chips_scroll)

        # Amount range filter
        amount_row = QWidget()
        amount_layout = QHBoxLayout(amount_row)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(6)

        amount_layout.addWidget(QLabel("Min ₹"))
        self._min_spin = QSpinBox()
        self._min_spin.setRange(0, 9_999_999)
        self._min_spin.setValue(0)
        self._min_spin.setFixedWidth(90)
        amount_layout.addWidget(self._min_spin)

        amount_layout.addWidget(QLabel("Max ₹"))
        self._max_spin = QSpinBox()
        self._max_spin.setRange(0, 9_999_999)
        self._max_spin.setValue(0)
        self._max_spin.setSpecialValueText("∞")
        self._max_spin.setFixedWidth(90)
        amount_layout.addWidget(self._max_spin)

        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(60)
        apply_btn.clicked.connect(self._apply_filters)
        amount_layout.addWidget(apply_btn)
        amount_layout.addStretch()
        tb_layout.addWidget(amount_row)

        # Date range filter + column visibility
        date_row = QWidget()
        date_layout = QHBoxLayout(date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(6)

        date_layout.addWidget(QLabel("From"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setSpecialValueText("Any")
        self._date_from.setMinimumDate(QDate(2000, 1, 1))
        self._date_from.setDate(self._date_from.minimumDate())
        self._date_from.dateChanged.connect(self._apply_filters)
        date_layout.addWidget(self._date_from)

        date_layout.addWidget(QLabel("To"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setSpecialValueText("Any")
        self._date_to.setMinimumDate(QDate(2000, 1, 1))
        self._date_to.setDate(self._date_to.minimumDate())
        self._date_to.dateChanged.connect(self._apply_filters)
        date_layout.addWidget(self._date_to)

        clear_date_btn = QPushButton("✕ Clear")
        clear_date_btn.setObjectName("ghostBtn")
        clear_date_btn.setFixedWidth(58)
        clear_date_btn.clicked.connect(self._clear_date_filters)
        date_layout.addWidget(clear_date_btn)

        date_layout.addSpacing(12)

        self._col_btn = QPushButton("Columns ▼")
        self._col_btn.setObjectName("ghostBtn")
        self._col_btn.clicked.connect(self._show_column_menu)
        date_layout.addWidget(self._col_btn)

        date_layout.addStretch()
        tb_layout.addWidget(date_row)

        layout.addWidget(toolbar)

        # ── Table ─────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.itemChanged.connect(self._on_item_changed)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(CI["✓"],          QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Date"],        QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Sender"],      QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(CI["Subject"],     QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Amount"],      QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Currency"],    QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Payment"],     QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Category"],    QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Tags"],        QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Confidence"],  QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Status"],      QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(CI["Sender"],  170)

        layout.addWidget(self._table, stretch=1)

        # ── Bulk action bar (hidden by default) ───────────────────────────
        self._bulk_bar = QWidget()
        self._bulk_bar.setObjectName("bulkBar")
        self._bulk_bar.setVisible(False)
        bulk_layout = QHBoxLayout(self._bulk_bar)
        bulk_layout.setContentsMargins(10, 4, 10, 4)

        self._bulk_label = QLabel("0 rows selected")
        self._bulk_label.setStyleSheet(f"color: #ffffff; font-weight: bold;")
        bulk_layout.addWidget(self._bulk_label)
        bulk_layout.addStretch()

        for text, slot in [
            ("Exclude Selected",  self._bulk_exclude),
            ("Change Category",   self._bulk_change_category),
            ("🔍 Mark for Review", self._bulk_mark_review),
            ("Export Selected",   self._bulk_export),
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet("background: rgba(255,255,255,0.15); color: #fff; border-radius:5px;")
            btn.clicked.connect(slot)
            bulk_layout.addWidget(btn)

        layout.addWidget(self._bulk_bar)

        # ── Summary row ───────────────────────────────────────────────────
        self._summary_label = QLabel("No data loaded")
        self._summary_label.setObjectName("statusLabel")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._summary_label)

        # Connect checkbox column header to select-all
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._table.itemSelectionChanged.connect(self._update_bulk_bar)

    # ── Filter logic ──────────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        query    = self._search.text().strip().lower()
        min_amt  = self._min_spin.value()
        max_amt  = self._max_spin.value()

        min_date_qdate = self._date_from.minimumDate()
        from_qdate     = self._date_from.date()
        to_qdate       = self._date_to.date()
        use_from = from_qdate > min_date_qdate
        use_to   = to_qdate   > min_date_qdate

        filtered = []
        for row in self._all_rows:
            # Category chip filter
            if self._active_categories:
                cat = row.get("category_edited") or row.get("category", "Other")
                if cat not in self._active_categories:
                    continue

            # Amount range
            amt = row.get("amount_edited") or row.get("amount") or 0
            if amt < min_amt:
                continue
            if max_amt > 0 and amt > max_amt:
                continue

            # Date range
            if use_from or use_to:
                date_str = (row.get("email_date") or "")[:10]
                if use_from and date_str < from_qdate.toString("yyyy-MM-dd"):
                    continue
                if use_to and date_str > to_qdate.toString("yyyy-MM-dd"):
                    continue

            # Text search
            if query:
                haystack = " ".join([
                    row.get("sender", ""),
                    row.get("sender_email", ""),
                    row.get("subject", ""),
                    row.get("category_edited") or row.get("category", ""),
                    row.get("tags", ""),
                ]).lower()
                if query not in haystack:
                    continue

            filtered.append(row)

        self._visible_rows = filtered
        self._populate_table(filtered)

    def _clear_date_filters(self) -> None:
        min_d = self._date_from.minimumDate()
        self._date_from.setDate(min_d)
        self._date_to.setDate(min_d)
        self._apply_filters()

    def _show_column_menu(self) -> None:
        from PyQt6.QtCore import QPoint
        menu = QMenu(self)
        for col_name in COLUMNS:
            if col_name == "✓":
                continue
            act = menu.addAction(col_name)
            act.setCheckable(True)
            act.setChecked(not self._table.isColumnHidden(CI[col_name]))
            act.toggled.connect(
                lambda checked, c=CI[col_name]: self._table.setColumnHidden(c, not checked)
            )
        menu.exec(self._col_btn.mapToGlobal(QPoint(0, self._col_btn.height())))

    def filter_by_category(self, category: str) -> None:
        """Called externally (e.g., chart drill-down) to filter to one category."""
        self._active_categories = {category}
        self._update_all_chip_state()
        self._apply_filters()

    def _populate_table(self, rows: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        self._table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            msg_id    = row.get("id", "")
            status    = row.get("status", "active")
            conf      = row.get("confidence", "LOW")
            cat       = row.get("category_edited") or row.get("category", "Other")
            amount    = row.get("amount_edited") or row.get("amount") or 0
            tags_raw  = row.get("tags", "[]")
            is_dup    = status == "duplicate"
            is_excl   = status == "excluded"

            try:
                tags_list = json.loads(tags_raw)
            except (ValueError, TypeError):
                tags_list = []

            sym = _currency_sym(row.get("currency", "INR"))

            is_edited_amt = row.get("amount_edited") is not None and row.get("amount_edited") != row.get("amount")
            is_edited_cat = row.get("category_edited") is not None and row.get("category_edited") != row.get("category")

            status_text = _status_label(status, is_dup)
            if status == "review":
                status_badge = f"🔍 {status_text}"
                status_badge_color = WARNING
            elif status == "excluded":
                status_badge = f"🚫 {status_text}"
                status_badge_color = TEXT_DIM
            else:
                status_badge = f"✓ {status_text}"
                status_badge_color = SUCCESS

            items = [
                _item("",               CI["✓"],          center=True),
                _item(row.get("email_date", ""), CI["Date"],     center=True),
                _item(_trunc(row.get("sender",""),28),  CI["Sender"]),
                _item(_trunc(row.get("subject",""),45), CI["Subject"]),
                _item(f"{sym}{amount:,.2f}", CI["Amount"],    right=True, bold=is_edited_amt),
                _item(row.get("currency","INR"),     CI["Currency"],  center=True),
                _item(_trunc(row.get("payment_method","Unknown"),22), CI["Payment"]),
                _item(_create_category_chip(cat), CI["Category"]),
                _item(", ".join(tags_list), CI["Tags"]),
                _item(_create_badge(
                    _conf_label(conf),
                    CONFIDENCE_BADGES.get(conf, CONFIDENCE_BADGES["NONE"])[0],
                    CONFIDENCE_BADGES.get(conf, CONFIDENCE_BADGES["NONE"])[1]
                ), CI["Confidence"]),
                _item(_create_badge(
                    status_badge,
                    "#1e3a26" if status == "active" else "#3a2628" if status == "excluded" else "#3a3528",
                    status_badge_color
                ), CI["Status"]),
            ]

            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, msg_id)
                self._table.setItem(r, col, item)

            # Checkbox
            chk_item = self._table.item(r, CI["✓"])
            chk_item.setCheckState(Qt.CheckState.Unchecked)
            chk_item.setFlags(chk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            # Numeric sort key for amount
            amt_item = self._table.item(r, CI["Amount"])
            amt_item.setData(Qt.ItemDataRole.UserRole + 1, amount)

            # Row appearance
            conf_color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["Other"])
            cat_item   = self._table.item(r, CI["Category"])
            cat_item.setForeground(QColor(conf_color))
            bold = QFont(); bold.setBold(True)
            cat_item.setFont(bold)

            # Confidence badge color + tooltip
            c_item = self._table.item(r, CI["Confidence"])
            c_item.setForeground(QColor(CONFIDENCE_COLORS.get(conf, TEXT_DIM)))
            source = row.get("classification_source", "")
            source_label = {
                "rules":        "Stage 1: Rule engine (keyword scoring)",
                "ml":           "Stage 2: TF-IDF + Naive Bayes",
                "distilbert":   "Stage 3: DistilBERT",
                "phi4-mini":    "Stage 3: phi4-mini via Ollama",
                "human_review": "Manually reviewed",
            }.get(source, source or "Unknown")
            c_item.setToolTip(f"Confidence: {conf}\nClassified by: {source_label}")

            if is_excl:
                for col in range(len(COLUMNS)):
                    it = self._table.item(r, col)
                    if it:
                        it.setForeground(QColor(TEXT_DIM))
                        f = it.font(); f.setStrikeOut(True); it.setFont(f)

            if is_dup:
                dup_item = self._table.item(r, CI["Status"])
                dup_item.setForeground(QColor(WARNING))

            if conf == "LOW":
                # Amber tint for row background of low-confidence
                for col in range(len(COLUMNS)):
                    it = self._table.item(r, col)
                    if it and not is_excl:
                        it.setBackground(QColor("#2a2318"))

        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)
        self._update_summary_label()
        self._update_bulk_bar()

    def _update_summary_label(self) -> None:
        total   = len(self._all_rows)
        visible = len(self._visible_rows)
        if total == 0:
            self._summary_label.setText("No data loaded")
            return
        total_amt = sum(
            (r.get("amount_edited") or r.get("amount") or 0)
            for r in self._visible_rows
            if r.get("status") != "excluded"
        )
        sym = _currency_sym("INR")
        self._summary_label.setText(
            f"Showing {visible} of {total} expenses · {sym}{total_amt:,.2f} total"
        )

    # ── Chip logic ────────────────────────────────────────────────────────────

    def _on_all_chip(self) -> None:
        self._active_categories.clear()
        self._update_all_chip_state()
        self._apply_filters()

    def _on_chip_toggled(self, category: str, checked: bool) -> None:
        if checked:
            self._active_categories.add(category)
        else:
            self._active_categories.discard(category)
        self._update_all_chip_state()
        self._apply_filters()

    def _update_all_chip_state(self) -> None:
        all_active = len(self._active_categories) == 0
        all_btn = self._chip_btns["All"]
        all_btn.setObjectName("chipActive" if all_active else "chipInactive")
        all_btn.setChecked(all_active)
        all_btn.style().unpolish(all_btn)
        all_btn.style().polish(all_btn)

        for cat, btn in self._chip_btns.items():
            if cat == "All":
                continue
            active = cat in self._active_categories
            btn.setObjectName("chipActive" if active else "chipInactive")
            btn.setChecked(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Header click (select all checkboxes) ─────────────────────────────────

    def _on_header_clicked(self, col: int) -> None:
        if col != CI["✓"]:
            return
        self._table.blockSignals(True)
        state = Qt.CheckState.Checked
        for r in range(self._table.rowCount()):
            item = self._table.item(r, CI["✓"])
            if item:
                item.setCheckState(state)
        self._table.blockSignals(False)
        self._update_bulk_bar()

    def _update_bulk_bar(self) -> None:
        checked = self._get_checked_msg_ids()
        visible = len(checked) > 0
        self._bulk_bar.setVisible(visible)
        if visible:
            self._bulk_label.setText(f"{len(checked)} row(s) selected")

    def _get_checked_msg_ids(self) -> list[str]:
        ids = []
        for r in range(self._table.rowCount()):
            item = self._table.item(r, CI["✓"])
            if item and item.checkState() == Qt.CheckState.Checked:
                msg_id = item.data(Qt.ItemDataRole.UserRole)
                if msg_id:
                    ids.append(msg_id)
        return ids

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def _bulk_exclude(self) -> None:
        ids = self._get_checked_msg_ids()
        for row in self._all_rows:
            if row.get("id") in ids:
                row["status"] = "excluded"
                self.field_changed.emit(row["id"], "status", "excluded")
        self._apply_filters()

    def _bulk_change_category(self) -> None:
        ids = self._get_checked_msg_ids()
        if not ids:
            return
        dlg = _CategoryPickerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cat = dlg.selected_category()
            for row in self._all_rows:
                if row.get("id") in ids:
                    row["category_edited"] = cat
                    self.field_changed.emit(row["id"], "category_edited", cat)
            self._apply_filters()

    def _bulk_mark_review(self) -> None:
        ids = set(self._get_checked_msg_ids())
        for row in self._all_rows:
            if row.get("id") in ids:
                row["status"] = "review"
                self.field_changed.emit(row["id"], "status", "review")
        self._apply_filters()

    def _bulk_export(self) -> None:
        from core.csv_exporter import export_to_csv
        ids  = set(self._get_checked_msg_ids())
        rows = [r for r in self._visible_rows if r.get("id") in ids]
        export_to_csv(self, rows, 0, 0)

    # ── Cell double-click (inline amount edit) ────────────────────────────────

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if col == CI["Amount"]:
            self._start_amount_edit(row)
        else:
            msg_id = self._table.item(row, 0)
            if msg_id:
                mid = msg_id.data(Qt.ItemDataRole.UserRole)
                exp = next((r for r in self._visible_rows if r.get("id") == mid), None)
                if exp:
                    dlg = _ExpenseDetailDialog(exp, self)
                    dlg.exec()

    def _start_amount_edit(self, row: int) -> None:
        item = self._table.item(row, CI["Amount"])
        if not item:
            return
        msg_id = item.data(Qt.ItemDataRole.UserRole)
        raw_amt = item.data(Qt.ItemDataRole.UserRole + 1) or 0

        editor = QLineEdit(self._table)
        editor.setText(f"{raw_amt:.2f}")
        editor.selectAll()
        self._table.setCellWidget(row, CI["Amount"], editor)
        editor.setFocus()

        def commit():
            try:
                new_val = float(editor.text().replace(",", ""))
                item.setText(f"₹{new_val:,.2f}")
                item.setData(Qt.ItemDataRole.UserRole + 1, new_val)
                for r in self._all_rows:
                    if r.get("id") == msg_id:
                        r["amount_edited"] = new_val
                self.field_changed.emit(msg_id, "amount_edited", new_val)
            except ValueError:
                pass
            finally:
                self._table.removeCellWidget(row, CI["Amount"])

        editor.editingFinished.connect(commit)
        editor.returnPressed.connect(commit)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        # Only react to checkbox changes
        if item.column() == CI["✓"]:
            self._update_bulk_bar()

    # ── Context menu ──────────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0 or row >= len(self._visible_rows):
            return
        exp = self._visible_rows[row]
        msg_id = exp.get("id", "")
        status = exp.get("status", "active")

        menu = QMenu(self)

        # Edit category
        cat_menu = menu.addMenu("✏️  Edit category")
        for cat in ALL_CATEGORIES:
            act = cat_menu.addAction(cat)
            act.triggered.connect(lambda _, c=cat, m=msg_id, e=exp: self._ctx_set_category(e, c))

        menu.addAction("🏷️  Add / edit tags").triggered.connect(
            lambda: self._ctx_edit_tags(exp)
        )
        menu.addSeparator()

        if status != "excluded":
            menu.addAction("🚫  Exclude this row").triggered.connect(
                lambda: self._ctx_exclude(exp, True)
            )
        else:
            menu.addAction("↩️  Un-exclude").triggered.connect(
                lambda: self._ctx_exclude(exp, False)
            )

        if status != "duplicate":
            menu.addAction("🔁  Mark as duplicate").triggered.connect(
                lambda: self._ctx_mark_dup(exp, True)
            )
        else:
            menu.addAction("🔁  Un-mark duplicate").triggered.connect(
                lambda: self._ctx_mark_dup(exp, False)
            )

        menu.addSeparator()
        if status != "review":
            menu.addAction("🔍  Mark for Review").triggered.connect(
                lambda: self._ctx_mark_review(exp, True)
            )
        else:
            menu.addAction("✅  Remove from Review").triggered.connect(
                lambda: self._ctx_mark_review(exp, False)
            )

        menu.addSeparator()
        menu.addAction("📋  View full email").triggered.connect(
            lambda: _ExpenseDetailDialog(exp, self).exec()
        )
        menu.addAction("📤  Export this row").triggered.connect(
            lambda: self._ctx_export_row(exp)
        )

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _ctx_set_category(self, exp: dict, cat: str) -> None:
        exp["category_edited"] = cat
        self.field_changed.emit(exp["id"], "category_edited", cat)
        self._apply_filters()

    def _ctx_edit_tags(self, exp: dict) -> None:
        dlg = _TagEditorDialog(exp, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tags = dlg.get_tags()
            tags_json = json.dumps(tags)
            exp["tags"] = tags_json
            self.field_changed.emit(exp["id"], "tags", tags_json)
            self._apply_filters()

    def _ctx_exclude(self, exp: dict, exclude: bool) -> None:
        new_status = "excluded" if exclude else "active"
        exp["status"] = new_status
        self.field_changed.emit(exp["id"], "status", new_status)
        self._apply_filters()

    def _ctx_mark_dup(self, exp: dict, is_dup: bool) -> None:
        new_status = "duplicate" if is_dup else "active"
        exp["status"] = new_status
        self.field_changed.emit(exp["id"], "status", new_status)
        self._apply_filters()

    def _ctx_mark_review(self, exp: dict, mark: bool) -> None:
        new_status = "review" if mark else "active"
        exp["status"] = new_status
        self.field_changed.emit(exp["id"], "status", new_status)
        if mark:
            self.review_requested.emit(exp["id"])
        self._apply_filters()

    def _ctx_export_row(self, exp: dict) -> None:
        from core.csv_exporter import export_to_csv
        export_to_csv(self, [exp], 0, 0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item(text: str, col: int, center: bool = False, right: bool = False, bold: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    elif right:
        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    else:
        it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    return it


def _currency_sym(currency: str) -> str:
    return {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")


def _trunc(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"


def _conf_label(conf: str) -> str:
    return {"HIGH": "High", "MEDIUM": "Med", "LOW": "Low", "NONE": "—"}.get(conf, conf)


def _status_label(status: str, is_dup: bool) -> str:
    if is_dup:
        return "Duplicate"
    return {"active": "Active", "excluded": "Excluded", "review": "Review", "duplicate": "Duplicate"}.get(status, status)


def _create_badge(text: str, bg_color: str, fg_color: str) -> str:
    """Create HTML badge styling."""
    return f"""
    <div style='
        background-color: {bg_color};
        color: {fg_color};
        padding: 3px 10px;
        border-radius: 12px;
        text-align: center;
        font-weight: 600;
        font-size: 11px;
    '>{text}</div>
    """


def _create_category_chip(category: str) -> str:
    """Create HTML for category with color indicator."""
    color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["Other"])
    return f"""
    <div style='display: flex; align-items: center; gap: 6px;'>
        <span style='
            width: 8px;
            height: 8px;
            background-color: {color};
            border-radius: 50%;
        '></span>
        <span style='font-weight: 500;'>{category}</span>
    </div>
    """


# ── Sub-dialogs ───────────────────────────────────────────────────────────────

class _ExpenseDetailDialog(QDialog):
    def __init__(self, exp: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Expense Detail")
        self.setMinimumSize(520, 400)
        layout = QVBoxLayout(self)

        title = QLabel(f"<b>{exp.get('subject','')}</b>")
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size:15px; color:{ACCENT};")
        layout.addWidget(title)

        cat   = exp.get("category_edited") or exp.get("category","Other")
        color = CATEGORY_COLORS.get(cat, "#888")
        sym   = _currency_sym(exp.get("currency","INR"))
        amt   = exp.get("amount_edited") or exp.get("amount") or 0

        for label, value in [
            ("Date",     exp.get("email_date","")),
            ("From",     f"{exp.get('sender','')} &lt;{exp.get('sender_email','')}&gt;"),
            ("Amount",   f"<b>{sym}{amt:,.2f}  {exp.get('currency','INR')}</b>"),
            ("Payment",  exp.get("payment_method","Unknown")),
            ("Category", f"<span style='color:{color};font-weight:bold'>{cat}</span>"),
            ("Confidence", exp.get("confidence","")),
            ("Snippet",  exp.get("snippet","—")),
        ]:
            row_w = QFrame()
            rl = QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0)
            lbl = QLabel(f"<span style='color:{TEXT_DIM}'>{label}:</span>")
            lbl.setFixedWidth(90)
            val = QLabel(value); val.setWordWrap(True)
            val.setTextFormat(Qt.TextFormat.RichText)
            rl.addWidget(lbl); rl.addWidget(val, stretch=1)
            layout.addWidget(row_w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


class _TagEditorDialog(QDialog):
    def __init__(self, exp: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Tags")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)

        try:
            self._tags: list[str] = json.loads(exp.get("tags", "[]") or "[]")
        except (ValueError, TypeError):
            self._tags = []

        layout.addWidget(QLabel("Current tags:"))
        self._tags_widget = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_widget)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tags_widget)
        self._refresh_tag_chips()

        add_row = QWidget()
        add_layout = QHBoxLayout(add_row)
        add_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("New tag…")
        self._tag_input.returnPressed.connect(self._add_tag)
        add_layout.addWidget(self._tag_input)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_tag)
        add_layout.addWidget(add_btn)
        layout.addWidget(add_row)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _add_tag(self) -> None:
        tag = self._tag_input.text().strip().lower()
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self._tag_input.clear()
            self._refresh_tag_chips()

    def _remove_tag(self, tag: str) -> None:
        if tag in self._tags:
            self._tags.remove(tag)
            self._refresh_tag_chips()

    def _refresh_tag_chips(self) -> None:
        while self._tags_layout.count():
            child = self._tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for tag in self._tags:
            chip = QPushButton(f"{tag}  ×")
            chip.setObjectName("chipActive")
            chip.clicked.connect(lambda _, t=tag: self._remove_tag(t))
            self._tags_layout.addWidget(chip)
        self._tags_layout.addStretch()

    def get_tags(self) -> list[str]:
        return list(self._tags)


class _CategoryPickerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Category")
        layout = QVBoxLayout(self)
        self._combo = QComboBox()
        for cat in ALL_CATEGORIES:
            self._combo.addItem(cat)
        layout.addWidget(self._combo)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_category(self) -> str:
        return self._combo.currentText()
