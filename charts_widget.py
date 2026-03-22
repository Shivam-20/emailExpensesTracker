"""
charts_widget.py — Matplotlib charts embedded in PyQt6.

Shows:
  • Chart A — Pie chart: Spending by Category
  • Chart B — Bar chart: Top 10 Expenses This Month
  • Summary cards row: Total Spent, Transactions, Top Category, Most Expensive Day
"""

import calendar
from collections import defaultdict
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")   # must be set before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget,
)

from expense_parser import Expense
from styles import (
    BG, SURFACE, SURFACE2, ACCENT, TEXT, TEXT_DIM, WARNING,
    SUCCESS, CATEGORY_COLORS,
)

# Matplotlib dark style settings
_MPL_BG   = BG
_MPL_FG   = TEXT
_MPL_GRID = "#45475a"


class ChartsWidget(QWidget):
    """
    Tab 2 — contains side-by-side matplotlib charts plus a summary card row.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._expenses: list[Expense] = []
        self._setup_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_charts(self, expenses: list[Expense]) -> None:
        """Re-render all charts and summary cards with *expenses*."""
        self._expenses = expenses
        self._render_charts()
        self._update_summary_cards()

    def clear(self) -> None:
        self._expenses = []
        self._render_charts()
        self._update_summary_cards()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Charts row ────────────────────────────────────────────────────
        charts_row = QWidget()
        charts_layout = QHBoxLayout(charts_row)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(12)

        # Pie chart
        self._pie_fig = Figure(figsize=(5, 4), facecolor=_MPL_BG, tight_layout=True)
        self._pie_ax  = self._pie_fig.add_subplot(111)
        self._pie_canvas = FigureCanvas(self._pie_fig)
        self._pie_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        charts_layout.addWidget(self._pie_canvas, stretch=1)

        # Bar chart
        self._bar_fig = Figure(figsize=(6, 4), facecolor=_MPL_BG, tight_layout=True)
        self._bar_ax  = self._bar_fig.add_subplot(111)
        self._bar_canvas = FigureCanvas(self._bar_fig)
        self._bar_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        charts_layout.addWidget(self._bar_canvas, stretch=1)

        layout.addWidget(charts_row, stretch=1)

        # ── Summary cards ─────────────────────────────────────────────────
        cards_row = QWidget()
        cards_layout = QHBoxLayout(cards_row)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)

        self._card_total       = _SummaryCard("💰 Total Spent",          "—")
        self._card_count       = _SummaryCard("📦 Total Transactions",   "—")
        self._card_top_cat     = _SummaryCard("🏆 Top Category",         "—")
        self._card_exp_day     = _SummaryCard("📅 Most Expensive Day",   "—")

        for card in (self._card_total, self._card_count,
                     self._card_top_cat, self._card_exp_day):
            cards_layout.addWidget(card, stretch=1)

        layout.addWidget(cards_row)

    # ── Chart rendering ───────────────────────────────────────────────────────

    def _render_charts(self) -> None:
        self._render_pie()
        self._render_bar()

    def _render_pie(self) -> None:
        ax = self._pie_ax
        ax.clear()
        ax.set_facecolor(_MPL_BG)
        self._pie_fig.patch.set_facecolor(_MPL_BG)

        if not self._expenses:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=TEXT_DIM, fontsize=13)
            self._pie_canvas.draw()
            return

        # Aggregate by category
        cat_totals: dict[str, float] = defaultdict(float)
        for e in self._expenses:
            cat_totals[e.category] += e.amount

        labels  = list(cat_totals.keys())
        values  = [cat_totals[l] for l in labels]
        colors  = [CATEGORY_COLORS.get(l, CATEGORY_COLORS["Other"]) for l in labels]

        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.82,
            wedgeprops={"linewidth": 1.5, "edgecolor": BG},
        )

        for at in autotexts:
            at.set_color(BG)
            at.set_fontsize(9)
            at.set_fontweight("bold")

        # Legend with amounts
        legend_labels = [f"{l}  ({_sym(self._expenses)}{v:,.0f})" for l, v in zip(labels, values)]
        ax.legend(
            wedges, legend_labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=2,
            fontsize=8,
            facecolor=SURFACE,
            edgecolor=_MPL_GRID,
            labelcolor=_MPL_FG,
            framealpha=0.9,
        )

        ax.set_title("Spending by Category", color=_MPL_FG, fontsize=13, pad=12)
        self._pie_canvas.draw()

    def _render_bar(self) -> None:
        ax = self._bar_ax
        ax.clear()
        ax.set_facecolor(SURFACE)
        self._bar_fig.patch.set_facecolor(_MPL_BG)

        if not self._expenses:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=TEXT_DIM, fontsize=13, transform=ax.transAxes)
            self._bar_canvas.draw()
            return

        # Top 10 by amount
        sorted_exp = sorted(self._expenses, key=lambda e: e.amount, reverse=True)[:10]

        labels = [_truncate(f"{e.sender}\n{e.subject}", 28) for e in sorted_exp]
        values = [e.amount for e in sorted_exp]
        colors = [CATEGORY_COLORS.get(e.category, CATEGORY_COLORS["Other"]) for e in sorted_exp]

        bars = ax.barh(range(len(sorted_exp)), values, color=colors,
                       height=0.6, edgecolor=BG, linewidth=0.8)

        # Value labels on bars
        sym = _sym(self._expenses)
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{sym}{val:,.0f}",
                va="center", ha="left",
                color=_MPL_FG, fontsize=8,
            )

        ax.set_yticks(range(len(sorted_exp)))
        ax.set_yticklabels(labels, fontsize=8, color=_MPL_FG)
        ax.invert_yaxis()
        ax.set_xlabel("Amount", color=_MPL_FG, fontsize=9)
        ax.set_title("Top 10 Expenses This Month", color=_MPL_FG, fontsize=13, pad=12)
        ax.tick_params(colors=_MPL_FG, labelsize=8)
        ax.spines[:].set_color(_MPL_GRID)
        ax.set_xlim(0, max(values) * 1.18)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.set_facecolor(SURFACE)
        ax.grid(axis="x", color=_MPL_GRID, linestyle="--", alpha=0.4)
        ax.xaxis.label.set_color(_MPL_FG)

        self._bar_canvas.draw()

    # ── Summary cards ─────────────────────────────────────────────────────────

    def _update_summary_cards(self) -> None:
        if not self._expenses:
            for card in (self._card_total, self._card_count,
                         self._card_top_cat, self._card_exp_day):
                card.set_value("—")
            return

        sym = _sym(self._expenses)
        total = sum(e.amount for e in self._expenses)
        count = len(self._expenses)

        # Top category
        cat_totals: dict[str, float] = defaultdict(float)
        for e in self._expenses:
            cat_totals[e.category] += e.amount
        top_cat, top_amt = max(cat_totals.items(), key=lambda x: x[1])

        # Most expensive day
        day_totals: dict[str, float] = defaultdict(float)
        for e in self._expenses:
            day_totals[e.date] += e.amount
        exp_day, _ = max(day_totals.items(), key=lambda x: x[1])
        # Format: "15 Mar"
        try:
            from datetime import datetime
            dt = datetime.strptime(exp_day, "%Y-%m-%d")
            exp_day_fmt = dt.strftime("%-d %b")
        except Exception:
            exp_day_fmt = exp_day

        self._card_total.set_value(f"{sym}{total:,.2f}")
        self._card_count.set_value(str(count))
        self._card_top_cat.set_value(f"{top_cat}\n({sym}{top_amt:,.0f})")
        self._card_exp_day.set_value(exp_day_fmt)


# ── Summary Card widget ───────────────────────────────────────────────────────

class _SummaryCard(QFrame):
    def __init__(self, title: str, value: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("cardLabel")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("cardValue")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setWordWrap(True)

        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)

    def set_value(self, value: str) -> None:
        self._value_lbl.setText(value)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sym(expenses: list[Expense]) -> str:
    """Return the dominant currency symbol for labelling."""
    if not expenses:
        return "₹"
    most_common = max(set(e.currency for e in expenses),
                      key=lambda c: sum(1 for e in expenses if e.currency == c))
    return {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(most_common, "")


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"
