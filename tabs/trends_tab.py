"""
tabs/trends_tab.py — Month-over-month line chart + comparison table.
"""

import calendar
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from config.category_map import ALL_CATEGORIES
from styles import BG, SURFACE, SURFACE2, TEXT, TEXT_DIM, BORDER, ACCENT, CATEGORY_COLORS

logger = logging.getLogger(__name__)


class TrendsTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db         = None
        self._data_dir:  Optional[Path] = None
        self._trend_data: dict = {}   # month_str → list[dict]
        self._setup_ui()

    def set_db(self, db, data_dir: Path) -> None:
        self._db       = db
        self._data_dir = data_dir

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Controls bar
        ctrl = QWidget()
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        ctrl_layout.addWidget(QLabel("Last"))
        self._n_spin = QSpinBox()
        self._n_spin.setRange(2, 12)
        self._n_spin.setValue(6)
        self._n_spin.setFixedWidth(60)
        ctrl_layout.addWidget(self._n_spin)
        ctrl_layout.addWidget(QLabel("months"))

        load_btn = QPushButton("📈 Load Trend")
        load_btn.setObjectName("primaryBtn")
        load_btn.clicked.connect(self._load_trend)
        ctrl_layout.addWidget(load_btn)

        export_btn = QPushButton("📥 Export CSV")
        export_btn.setObjectName("ghostBtn")
        export_btn.clicked.connect(self._export_csv)
        ctrl_layout.addWidget(export_btn)

        ctrl_layout.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        ctrl_layout.addWidget(self._status_lbl)

        layout.addWidget(ctrl)

        # Chart
        self._fig  = Figure(figsize=(9, 4), facecolor=BG, tight_layout=True)
        self._ax   = self._fig.add_subplot(111)
        self._canv = FigureCanvas(self._fig)
        self._canv.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._canv, stretch=1)

        # Comparison table
        layout.addWidget(QLabel("Month Comparison"))
        self._table = QTableWidget()
        self._table.setMinimumHeight(100)
        self._table.setMaximumHeight(260)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_trend(self) -> None:
        if not self._db:
            self._status_lbl.setText("No data — fetch expenses first.")
            return

        n = self._n_spin.value()
        now = datetime.now()

        # Build list of month strings going backwards
        months: list[str] = []
        y, m = now.year, now.month
        for _ in range(n):
            months.insert(0, f"{y}-{m:02d}")
            m -= 1
            if m < 1:
                m = 12; y -= 1

        try:
            rows = self._db.get_months_expenses(months)
        except Exception as exc:
            self._status_lbl.setText(f"Error loading trend: {exc}")
            return

        # Group rows by month
        month_data: dict[str, list[dict]] = {m: [] for m in months}
        for row in rows:
            mth = str(row["month"])
            if mth in month_data:
                month_data[mth].append(dict(row))

        self._trend_data = month_data
        self._render_trend(months, month_data, now)
        self._render_table(months, month_data)
        self._status_lbl.setText(f"Showing {n} months of data")

    # ── Chart renderer ────────────────────────────────────────────────────────

    def _render_trend(
        self,
        months: list[str],
        month_data: dict,
        now: datetime,
    ) -> None:
        ax  = self._ax
        fig = self._fig
        ax.clear()
        ax.set_facecolor(SURFACE)
        fig.patch.set_facecolor(BG)

        # Top 5 categories by total spend
        cat_totals: dict[str, float] = defaultdict(float)
        for rows in month_data.values():
            for r in rows:
                cat = r.get("category_edited") or r.get("category","Other")
                cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cats = sorted(cat_totals, key=lambda c: cat_totals[c], reverse=True)[:5]

        x_labels = [_short_month(m) for m in months]
        x        = list(range(len(months)))

        cat_palette = [
            CATEGORY_COLORS.get(c, "#89b4fa") for c in top_cats
        ]

        for cat, color in zip(top_cats, cat_palette):
            y_vals = []
            for m in months:
                total = sum(
                    (r.get("amount_edited") or r.get("amount") or 0)
                    for r in month_data[m]
                    if (r.get("category_edited") or r.get("category","Other")) == cat
                )
                y_vals.append(total)
            ax.plot(x, y_vals, marker="o", label=cat, color=color, linewidth=1.8)

        # Total line
        totals = [
            sum(r.get("amount_edited") or r.get("amount") or 0 for r in month_data[m])
            for m in months
        ]
        ax.plot(x, totals, marker="o", label="Total", color=TEXT,
                linewidth=2.5, linestyle="--", zorder=5)

        # Current month vertical dashed marker
        current = f"{now.year}-{now.month:02d}"
        if current in months:
            ci = months.index(current)
            ax.axvline(ci, color=ACCENT, linestyle=":", linewidth=1.5, alpha=0.8)

        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=TEXT_DIM, fontsize=9)
        ax.tick_params(colors=TEXT_DIM)
        ax.set_ylabel("Amount (₹)", color=TEXT_DIM, fontsize=9)
        ax.set_title("Month-over-Month Spending", color=TEXT, fontsize=13, pad=12)
        ax.spines[:].set_color(BORDER)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=BORDER, linestyle="--", alpha=0.3)
        ax.legend(
            loc="lower center", bbox_to_anchor=(0.5, -0.22),
            ncol=len(top_cats) + 1, fontsize=8,
            facecolor=SURFACE, edgecolor=BORDER, labelcolor=TEXT,
        )
        self._canv.draw()

    def _export_csv(self) -> None:
        if not self._trend_data:
            self._status_lbl.setText("No trend data to export — load trend first.")
            return
        from PyQt6.QtWidgets import QFileDialog
        import csv as _csv
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Trend CSV", "trend_comparison.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        months = sorted(self._trend_data.keys())
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = _csv.writer(fh)
                writer.writerow(["month", "total", "count", "avg_transaction"])
                for m in months:
                    rows = self._trend_data[m]
                    active = [r for r in rows if r.get("status") != "excluded"]
                    total = sum(r.get("amount_edited") or r.get("amount") or 0 for r in active)
                    count = len(active)
                    avg   = total / count if count else 0
                    writer.writerow([m, f"{total:.2f}", count, f"{avg:.2f}"])
            self._status_lbl.setText(f"Exported to {path}")
        except OSError as exc:
            self._status_lbl.setText(f"Export failed: {exc}")

    # ── Comparison table ──────────────────────────────────────────────────────

    def _render_table(
        self,
        months: list[str],
        month_data: dict,
    ) -> None:
        # Dynamically compute top-4 categories across all loaded months
        from collections import defaultdict as _dd
        all_cat_totals: dict[str, float] = _dd(float)
        for rows in month_data.values():
            for r in rows:
                cat = r.get("category_edited") or r.get("category", "Other")
                all_cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cats = sorted(all_cat_totals, key=lambda c: all_cat_totals[c], reverse=True)[:4]

        col_names = ["Month", "Total"] + top_cats + ["Others", "vs Prev"]
        self._table.setColumnCount(len(col_names))
        self._table.setHorizontalHeaderLabels(col_names)
        self._table.setRowCount(len(months))
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        prev_total: float = 0

        for row_i, m in enumerate(months):
            rows = month_data[m]
            total = sum(r.get("amount_edited") or r.get("amount") or 0 for r in rows)
            cat_totals: dict[str, float] = defaultdict(float)
            for r in rows:
                cat = r.get("category_edited") or r.get("category","Other")
                cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
            others = total - sum(cat_totals.get(c, 0) for c in top_cats)

            vs_prev = ""
            if row_i > 0 and prev_total > 0:
                pct = (total - prev_total) / prev_total * 100
                arrow = "↑" if pct >= 0 else "↓"
                vs_prev = f"{arrow} {abs(pct):.1f}%"

            values = (
                [_short_month(m), f"₹{total:,.0f}"]
                + [f"₹{cat_totals.get(c,0):,.0f}" for c in top_cats]
                + [f"₹{others:,.0f}", vs_prev]
            )
            for col_i, val in enumerate(values):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row_i, col_i, it)

            prev_total = total


# ── Helpers ───────────────────────────────────────────────────────────────────

def _short_month(month_str: str) -> str:
    try:
        dt = datetime.strptime(month_str, "%Y-%m")
        return dt.strftime("%b %y")
    except ValueError:
        return month_str
