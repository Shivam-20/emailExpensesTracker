"""
expense_table.py — QTableWidget panel for displaying and filtering expenses.

Features
--------
- Live search/filter bar
- Sortable columns
- Alternating row colors
- Category cells are color-coded
- Double-click row opens a detail dialog
- Row count label
"""

import calendar
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from expense_parser import Expense
from styles import CATEGORY_COLORS, TEXT_DIM, SURFACE, SURFACE2, ACCENT, TEXT

# ── Column definitions ────────────────────────────────────────────────────────
COLUMNS = ["#", "Date", "Sender", "Subject", "Amount", "Currency", "Category"]
COL_IDX = {name: i for i, name in enumerate(COLUMNS)}


class ExpenseTableWidget(QWidget):
    """
    Full expense table panel: search bar + QTableWidget + row count label.
    """

    row_double_clicked = pyqtSignal(object)  # emits the Expense object

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all_expenses: list[Expense] = []
        self._visible_expenses: list[Expense] = []
        self._setup_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_expenses(self, expenses: list[Expense]) -> None:
        """Populate the table with a fresh list of Expense objects."""
        self._all_expenses = expenses
        self._apply_filter(self._search_bar.text())

    def get_visible_expenses(self) -> list[Expense]:
        """Return expenses currently shown (respecting active filter)."""
        return list(self._visible_expenses)

    def clear(self) -> None:
        self._all_expenses = []
        self._visible_expenses = []
        self._table.setRowCount(0)
        self._update_row_count_label()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # Search bar
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText(
            "🔍 Search sender, subject, category…"
        )
        self._search_bar.setClearButtonEnabled(True)
        self._search_bar.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search_bar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(True)

        # Column stretch
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_IDX["#"],        QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_IDX["Date"],     QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_IDX["Sender"],   QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(COL_IDX["Subject"],  QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_IDX["Amount"],   QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_IDX["Currency"], QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_IDX["Category"], QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(COL_IDX["Sender"], 180)

        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Row count label
        self._count_label = QLabel("No data loaded")
        self._count_label.setObjectName("statusLabel")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_label)

    # ── Filter logic ──────────────────────────────────────────────────────────

    def _apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        if q:
            filtered = [
                e for e in self._all_expenses
                if q in e.sender.lower()
                or q in e.sender_email.lower()
                or q in e.subject.lower()
                or q in e.category.lower()
            ]
        else:
            filtered = list(self._all_expenses)

        self._visible_expenses = filtered
        self._populate_table(filtered)

    def _populate_table(self, expenses: list[Expense]) -> None:
        # Disable sorting during bulk insert (performance)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setRowCount(len(expenses))

        for row, exp in enumerate(expenses):
            currency_sym = _currency_symbol(exp.currency)
            amount_str   = f"{currency_sym}{exp.amount:,.2f}"

            items = [
                _make_item(str(row + 1), align=Qt.AlignmentFlag.AlignCenter),
                _make_item(exp.date,     align=Qt.AlignmentFlag.AlignCenter),
                _make_item(exp.sender),
                _make_item(exp.subject),
                _make_item(amount_str,   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                _make_item(exp.currency, align=Qt.AlignmentFlag.AlignCenter),
                _make_item(exp.category, align=Qt.AlignmentFlag.AlignCenter),
            ]

            for col, item in enumerate(items):
                # Store raw numeric amount for proper numeric sort
                if col == COL_IDX["Amount"]:
                    item.setData(Qt.ItemDataRole.UserRole, exp.amount)
                self._table.setItem(row, col, item)

            # Color-code the Category cell
            cat_item = self._table.item(row, COL_IDX["Category"])
            color_hex = CATEGORY_COLORS.get(exp.category, CATEGORY_COLORS["Other"])
            cat_item.setForeground(QColor(color_hex))
            font = QFont()
            font.setBold(True)
            cat_item.setFont(font)

        self._table.setSortingEnabled(True)
        self._update_row_count_label()

    def _update_row_count_label(self) -> None:
        total   = len(self._all_expenses)
        visible = len(self._visible_expenses)
        if total == 0:
            self._count_label.setText("No data loaded")
        elif visible == total:
            self._count_label.setText(f"Showing {total} expense(s)")
        else:
            self._count_label.setText(f"Showing {visible} of {total} expenses")

    # ── Double-click handler ──────────────────────────────────────────────────

    def _on_double_click(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._visible_expenses):
            exp = self._visible_expenses[row]
            dlg = ExpenseDetailDialog(exp, self)
            dlg.exec()


# ── Detail Dialog ─────────────────────────────────────────────────────────────

class ExpenseDetailDialog(QDialog):
    """Shows full details of a single expense in a scrollable dialog."""

    def __init__(self, expense: Expense, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Expense Detail")
        self.setMinimumSize(520, 420)
        self._build_ui(expense)

    def _build_ui(self, exp: Expense) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel(f"<b>{exp.subject}</b>")
        header.setWordWrap(True)
        header.setStyleSheet(f"font-size: 15px; color: {ACCENT};")
        layout.addWidget(header)

        # Fields
        color_hex = CATEGORY_COLORS.get(exp.category, CATEGORY_COLORS["Other"])
        currency_sym = _currency_symbol(exp.currency)

        fields = [
            ("Date",      exp.date),
            ("From",      f"{exp.sender}  &lt;{exp.sender_email}&gt;"),
            ("Amount",    f"<b>{currency_sym}{exp.amount:,.2f}  {exp.currency}</b>"),
            ("Category",  f"<span style='color:{color_hex};font-weight:bold'>{exp.category}</span>"),
            ("Snippet",   exp.snippet or "—"),
        ]

        for label, value in fields:
            row_widget = QFrame()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"<span style='color:{TEXT_DIM}'>{label}:</span>")
            lbl.setFixedWidth(80)
            val = QLabel(value)
            val.setWordWrap(True)
            val.setTextFormat(Qt.TextFormat.RichText)
            row_layout.addWidget(lbl)
            row_layout.addWidget(val, stretch=1)
            layout.addWidget(row_widget)

        # Body preview
        if exp.body_preview.strip():
            layout.addWidget(_separator())
            layout.addWidget(QLabel("Email Preview:"))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            preview = QLabel(exp.body_preview[:1500])
            preview.setWordWrap(True)
            preview.setStyleSheet(f"background:{SURFACE2}; padding:8px; color:{TEXT_DIM}; font-size:11px;")
            scroll.setWidget(preview)
            layout.addWidget(scroll)

        # Close button
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_item(text: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(align)
    return item


def _currency_symbol(currency: str) -> str:
    return {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setObjectName("separator")
    return line
