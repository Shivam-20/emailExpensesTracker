"""
tabs/charts_tab.py — 2×2 matplotlib chart grid.

Chart A: Category pie
Chart B: Top-10 bar
Chart C: Payment method donut
Chart D: Daily spend heatmap
+ 4 summary stat cards below
"""

import calendar
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QGridLayout, QWidget,
)

from styles import (
    BG, SURFACE, SURFACE2, SURFACE3, ACCENT, TEXT, TEXT_DIM,
    BORDER, SUCCESS, WARNING, CATEGORY_COLORS,
)

logger = logging.getLogger(__name__)

_BG = BG
_FG = TEXT
_GRID = BORDER
plt.style.use("dark_background")


class ChartsTab(QWidget):
    # Emitted when user clicks a category in pie chart → drill down to expenses tab
    category_drill = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self._year  = datetime.now().year
        self._month = datetime.now().month
        self._prev_total: Optional[float] = None
        self._pie_labels: list[str] = []   # for pick-event drill-down
        self._setup_ui()

    def update_charts(self, rows: list[dict], year: int = 0, month: int = 0,
                      prev_total: Optional[float] = None) -> None:
        self._rows  = [r for r in rows if r.get("status") != "excluded"]
        if year:  self._year  = year
        if month: self._month = month
        self._prev_total = prev_total
        self._render_all()
        self._update_cards()

    def clear(self) -> None:
        self._rows = []
        self._prev_total = None
        self._render_all()
        self._update_cards()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        # Toolbar
        toolbar = QWidget()
        tb_lay  = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.addStretch()
        save_btn = QPushButton("💾 Save Charts")
        save_btn.setObjectName("ghostBtn")
        save_btn.setToolTip("Save all charts as a PNG image")
        save_btn.clicked.connect(self._save_charts)
        tb_lay.addWidget(save_btn)
        outer.addWidget(toolbar)

        # 2×2 chart grid
        grid = QWidget()
        self._chart_grid = grid
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(8)

        def _make_canvas(w=5, h=4) -> tuple[Figure, any, FigureCanvas]:
            fig  = Figure(figsize=(w, h), facecolor=_BG, tight_layout=True)
            ax   = fig.add_subplot(111)
            canv = FigureCanvas(fig)
            canv.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            return fig, ax, canv

        self._pie_fig, self._pie_ax, self._pie_canvas = _make_canvas()
        self._bar_fig, self._bar_ax, self._bar_canvas = _make_canvas()
        self._don_fig, self._don_ax, self._don_canvas = _make_canvas()
        self._heat_fig, self._heat_ax, self._heat_canvas = _make_canvas()

        grid_layout.addWidget(self._pie_canvas,  0, 0)
        grid_layout.addWidget(self._bar_canvas,  0, 1)
        grid_layout.addWidget(self._don_canvas,  1, 0)
        grid_layout.addWidget(self._heat_canvas, 1, 1)
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)

        # Connect heatmap hover + pie click for drill-down
        self._heat_canvas.mpl_connect("motion_notify_event", self._on_heat_hover)
        self._pie_canvas.mpl_connect("pick_event", self._on_pie_pick)

        outer.addWidget(grid, stretch=1)

        # Summary stat cards
        cards_row = QWidget()
        cards_layout = QHBoxLayout(cards_row)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(8)

        self._card_total   = _Card("💰 Total")
        self._card_count   = _Card("📦 Count")
        self._card_avg_day = _Card("📅 Avg/Day")
        self._card_biggest = _Card("🏆 Biggest")

        for card in (self._card_total, self._card_count,
                     self._card_avg_day, self._card_biggest):
            cards_layout.addWidget(card, stretch=1)

        outer.addWidget(cards_row)

    # ── Renderers ─────────────────────────────────────────────────────────────

    def _render_all(self) -> None:
        self._render_pie()
        self._render_bar()
        self._render_donut()
        self._render_heatmap()

    def _render_pie(self) -> None:
        ax = self._pie_ax
        ax.clear()
        ax.set_facecolor(_BG)
        self._pie_fig.patch.set_facecolor(_BG)

        if not self._rows:
            _no_data(ax, "Spending by Category")
            self._pie_canvas.draw()
            return

        cat_totals: dict[str, float] = defaultdict(float)
        for r in self._rows:
            cat = r.get("category_edited") or r.get("category", "Other")
            cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0

        labels = list(cat_totals.keys())
        values = [cat_totals[l] for l in labels]
        colors = [CATEGORY_COLORS.get(l, "#6c7086") for l in labels]

        self._pie_labels = labels   # store for pick-event drill-down

        wedges, _, autotexts = ax.pie(
            values, colors=colors, autopct="%1.1f%%",
            startangle=140, pctdistance=0.80,
            wedgeprops={"linewidth": 1.2, "edgecolor": _BG},
        )
        for w in wedges:
            w.set_picker(True)
        for at in autotexts:
            at.set_color(_BG); at.set_fontsize(8); at.set_fontweight("bold")

        sym = _dom_sym(self._rows)
        legend_labels = [f"{l}  ({sym}{v:,.0f})" for l, v in zip(labels, values)]
        ax.legend(
            wedges, legend_labels,
            loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2,
            fontsize=8, facecolor=SURFACE, edgecolor=_GRID,
            labelcolor=_FG, framealpha=0.9,
        )
        ax.set_title("Spending by Category", color=_FG, fontsize=12, pad=10)
        self._pie_canvas.draw()

    def _render_bar(self) -> None:
        ax = self._bar_ax
        ax.clear()
        ax.set_facecolor(SURFACE)
        self._bar_fig.patch.set_facecolor(_BG)

        if not self._rows:
            _no_data(ax, "Top 10 Transactions")
            self._bar_canvas.draw()
            return

        top10 = sorted(self._rows,
                       key=lambda r: r.get("amount_edited") or r.get("amount") or 0,
                       reverse=True)[:10]

        labels = [_trunc(r.get("sender", "?"), 25) for r in top10]
        values = [r.get("amount_edited") or r.get("amount") or 0 for r in top10]
        colors = [CATEGORY_COLORS.get(
            r.get("category_edited") or r.get("category","Other"), "#6c7086"
        ) for r in top10]
        sym = _dom_sym(self._rows)

        bars = ax.barh(range(len(top10)), values, color=colors,
                       height=0.6, edgecolor=_BG, linewidth=0.8)
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{sym}{val:,.0f}",
                va="center", ha="left", color=_FG, fontsize=8,
            )

        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels(labels, fontsize=8, color=_FG)
        ax.invert_yaxis()
        ax.set_xlabel("Amount", color=_FG, fontsize=9)
        ax.set_title("Top 10 Transactions", color=_FG, fontsize=12, pad=10)
        ax.tick_params(colors=_FG)
        ax.spines[:].set_color(_GRID)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        if values:
            ax.set_xlim(0, max(values) * 1.18)
        ax.grid(axis="x", color=_GRID, linestyle="--", alpha=0.4)
        self._bar_canvas.draw()

    def _render_donut(self) -> None:
        ax = self._don_ax
        ax.clear()
        ax.set_facecolor(_BG)
        self._don_fig.patch.set_facecolor(_BG)

        if not self._rows:
            _no_data(ax, "By Payment Method")
            self._don_canvas.draw()
            return

        pm_totals: dict[str, int] = defaultdict(int)
        for r in self._rows:
            method = r.get("payment_method", "Unknown")
            # Normalise "Credit Card ••1234" → "Credit Card"
            base = method.split(" ••")[0].split(" •")[0]
            pm_totals[base] += 1

        labels = list(pm_totals.keys())
        values = [pm_totals[l] for l in labels]

        palette = [
            "#89b4fa", "#cba6f7", "#a6e3a1", "#fab387",
            "#f9e2af", "#94e2d5", "#6c7086",
        ]
        colors = [palette[i % len(palette)] for i in range(len(labels))]

        wedges, _ = ax.pie(
            values, colors=colors, startangle=90,
            wedgeprops={"linewidth": 1.5, "edgecolor": _BG, "width": 0.5},
        )
        total = sum(values)
        ax.text(0, 0, str(total), ha="center", va="center",
                color=_FG, fontsize=14, fontweight="bold")

        ax.legend(
            wedges, [f"{l} ({v})" for l, v in zip(labels, values)],
            loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2,
            fontsize=8, facecolor=SURFACE, edgecolor=_GRID,
            labelcolor=_FG,
        )
        ax.set_title("By Payment Method", color=_FG, fontsize=12, pad=10)
        self._don_canvas.draw()

    def _render_heatmap(self) -> None:
        ax   = self._heat_ax
        fig  = self._heat_fig
        ax.clear()
        ax.set_facecolor(_BG)
        fig.patch.set_facecolor(_BG)

        year, month = self._year, self._month
        ax.set_title(
            f"Daily Spending — {calendar.month_name[month]} {year}",
            color=_FG, fontsize=12, pad=10,
        )

        if not self._rows:
            ax.axis("off")
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=TEXT_DIM, transform=ax.transAxes)
            self._heat_canvas.draw()
            return

        # Build day → total dict
        day_totals: dict[int, float] = defaultdict(float)
        for r in self._rows:
            date_str = r.get("email_date", "")
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if dt.year == year and dt.month == month:
                    day_totals[dt.day] += r.get("amount_edited") or r.get("amount") or 0
            except ValueError:
                pass

        # Calendar grid
        first_wd, num_days = calendar.monthrange(year, month)
        ncols = 7
        nrows = (first_wd + num_days + 6) // 7

        data   = [[0.0] * ncols for _ in range(nrows)]
        labels_grid = [[""] * ncols for _ in range(nrows)]

        for day in range(1, num_days + 1):
            pos   = first_wd + day - 1
            row_i = pos // ncols
            col_i = pos % ncols
            data[row_i][col_i]   = day_totals.get(day, 0.0)
            labels_grid[row_i][col_i] = str(day)

        import numpy as np
        arr = np.array(data)
        im  = ax.imshow(arr, cmap="Purples", aspect="auto",
                        vmin=0, vmax=max(arr.max(), 1))

        ax.set_xticks(range(7))
        ax.set_xticklabels(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                           color=TEXT_DIM, fontsize=8)
        ax.set_yticks([])
        ax.tick_params(colors=_FG)

        sym = _dom_sym(self._rows)
        for r in range(nrows):
            for c in range(ncols):
                if labels_grid[r][c]:
                    val = data[r][c]
                    text_color = _BG if val > arr.max() * 0.5 else _FG
                    ax.text(c, r, labels_grid[r][c],
                            ha="center", va="center",
                            fontsize=8, color=text_color, fontweight="bold")
                    if val > 0:
                        ax.text(c, r + 0.28,
                                f"{sym}{val:,.0f}",
                                ha="center", va="center",
                                fontsize=6, color=text_color, alpha=0.9)

        ax.spines[:].set_visible(False)
        self._heat_day_totals = day_totals
        self._heat_first_wd   = first_wd
        self._heat_num_days   = num_days
        self._heat_sym        = sym
        self._heat_canvas.draw()

    def _on_pie_pick(self, event) -> None:
        """Drill down to expenses tab when a pie wedge is clicked."""
        if not hasattr(event, "artist") or not self._pie_labels:
            return
        try:
            # Find which wedge index was picked
            ax = self._pie_ax
            wedges = [p for p in ax.patches]
            idx = wedges.index(event.artist)
            if 0 <= idx < len(self._pie_labels):
                self.category_drill.emit(self._pie_labels[idx])
        except (ValueError, AttributeError):
            pass

    def _save_charts(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Charts", "expense_charts.png",
            "PNG Image (*.png);;All Files (*)"
        )
        if path:
            pixmap = self._chart_grid.grab()
            pixmap.save(path)

    def _on_heat_hover(self, event) -> None:
        if not hasattr(self, "_heat_day_totals") or event.inaxes != self._heat_ax:
            return
        col = int(round(event.xdata)) if event.xdata is not None else -1
        row = int(round(event.ydata)) if event.ydata is not None else -1
        pos = row * 7 + col - self._heat_first_wd + 1
        if 1 <= pos <= self._heat_num_days:
            total = self._heat_day_totals.get(pos, 0)
            sym   = getattr(self, "_heat_sym", "₹")
            self._heat_canvas.setToolTip(
                f"{calendar.month_name[self._month]} {pos}, {self._year}: "
                f"{sym}{total:,.2f}"
            )
        else:
            self._heat_canvas.setToolTip("")

    # ── Cards ─────────────────────────────────────────────────────────────────

    def _update_cards(self) -> None:
        if not self._rows:
            for card in (self._card_total, self._card_count,
                         self._card_avg_day, self._card_biggest):
                card.set_value("—")
            return

        sym    = _dom_sym(self._rows)
        total  = sum(r.get("amount_edited") or r.get("amount") or 0 for r in self._rows)
        count  = len(self._rows)
        _, num_days = calendar.monthrange(self._year, self._month)
        avg_day = total / num_days if num_days else 0

        biggest = max(self._rows,
                      key=lambda r: r.get("amount_edited") or r.get("amount") or 0)
        big_amt = biggest.get("amount_edited") or biggest.get("amount") or 0
        big_who = _trunc(biggest.get("sender", "?"), 15)

        delta_str = ""
        if self._prev_total and self._prev_total > 0:
            delta_pct = (total - self._prev_total) / self._prev_total * 100
            arrow = "↑" if delta_pct >= 0 else "↓"
            delta_str = f"\n{arrow}{abs(delta_pct):.1f}% vs prev"

        self._card_total.set_value(f"{sym}{total:,.2f}{delta_str}")
        self._card_count.set_value(str(count))
        self._card_avg_day.set_value(f"{sym}{avg_day:,.2f}")
        self._card_biggest.set_value(f"{sym}{big_amt:,.0f}\n({big_who})")


# ── Helper widgets & functions ────────────────────────────────────────────────

class _Card(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        t = QLabel(title); t.setObjectName("cardLabel")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v = QLabel("—"); self._v.setObjectName("cardValue")
        self._v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v.setWordWrap(True)
        lay.addWidget(t); lay.addWidget(self._v)

    def set_value(self, val: str) -> None:
        self._v.setText(val)


def _no_data(ax, title: str) -> None:
    ax.set_facecolor(BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center",
            color=TEXT_DIM, fontsize=12, transform=ax.transAxes)
    ax.set_title(title, color=TEXT, fontsize=12)
    ax.axis("off")


def _dom_sym(rows: list[dict]) -> str:
    if not rows:
        return "₹"
    currencies = [r.get("currency", "INR") for r in rows]
    dominant = max(set(currencies), key=currencies.count)
    return {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(dominant, "")


def _trunc(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"
