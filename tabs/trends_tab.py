
"""
tabs/trends_tab.py — Month-over-month line chart + comparison table using TkAgg.
"""

import calendar
import csv as _csv
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.figure import Figure

from styles import BG, SURFACE, TEXT, TEXT_DIM, BORDER, ACCENT, CATEGORY_COLORS, bind_tree_scroll

logger = logging.getLogger(__name__)


class TrendsTab:
    """Tab 3 — Month-over-month spending line chart + comparison table."""

    def __init__(self, parent) -> None:
        self._parent    = parent
        self._db        = None
        self._data_dir: Optional[Path] = None
        self._trend_data: dict = {}
        self._setup_ui()

    def set_db(self, db, data_dir: Path) -> None:
        self._db       = db
        self._data_dir = data_dir

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        frame = ctk.CTkFrame(self._parent, fg_color=BG, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Controls bar
        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(ctrl, text="Last", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 4))

        self._n_var = ctk.StringVar(value="6")
        self._n_entry = ctk.CTkEntry(ctrl, textvariable=self._n_var, width=48,
                                      font=ctk.CTkFont(family="Inter", size=12),
                                      fg_color=SURFACE, border_color=BORDER, text_color=TEXT)
        self._n_entry.pack(side="left", padx=(0, 4))

        ctk.CTkLabel(ctrl, text="months", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 8))

        ctk.CTkButton(ctrl, text="📈 Load Trend", command=self._load_trend,
                       font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                       fg_color=ACCENT, hover_color=ACCENT, text_color="#1e1e2e",
                       corner_radius=8, height=28, width=110).pack(side="left", padx=(0, 8))

        ctk.CTkButton(ctrl, text="📥 Export CSV", command=self._export_csv,
                       font=ctk.CTkFont(family="Inter", size=12),
                       fg_color="transparent", hover_color=SURFACE, text_color=ACCENT,
                       border_color=ACCENT, border_width=1, corner_radius=8,
                       height=28, width=100).pack(side="left")

        self._status_lbl = ctk.CTkLabel(ctrl, text="", text_color=TEXT_DIM,
                                         font=ctk.CTkFont(family="Inter", size=11))
        self._status_lbl.pack(side="right")

        # Chart
        self._fig  = Figure(figsize=(9, 4), facecolor=BG, tight_layout=True)
        self._ax   = self._fig.add_subplot(111)
        self._canv = FigureCanvas(self._fig, master=frame)
        self._canv.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self._canv.get_tk_widget().pack(fill="both", expand=True)

        # Comparison table header
        ctk.CTkLabel(frame, text="Month Comparison",
                      font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                      text_color=TEXT, anchor="w").pack(anchor="w", padx=4, pady=(8, 4))

        # ttk Treeview for comparison table
        import tkinter.ttk as ttk
        import tkinter as tk
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Trends.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=24, font=("Inter", 10))
        style.configure("Trends.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"))
        style.map("Trends.Treeview", background=[("selected", "#313244")])

        tree_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=6)
        tree_frame.pack(fill="x", padx=0, pady=(0, 4))

        self._tree = ttk.Treeview(tree_frame, style="Trends.Treeview", height=5,
                                    show="headings", selectmode="browse")
        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)

        tree_vsb.pack(side="right", fill="y")
        tree_hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)
        bind_tree_scroll(self._tree)

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_trend(self) -> None:
        if not self._db:
            self._status_lbl.configure(text="No data — fetch expenses first.")
            return

        try:
            n = int(self._n_var.get())
            n = max(2, min(12, n))
        except ValueError:
            n = 6

        now = datetime.now()
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
            self._status_lbl.configure(text=f"Error: {exc}")
            return

        month_data: dict[str, list[dict]] = {m: [] for m in months}
        for row in rows:
            mth = str(row["month"])
            if mth in month_data:
                month_data[mth].append(dict(row))

        self._trend_data = month_data
        self._render_trend(months, month_data, now)
        self._render_table(months, month_data)
        self._status_lbl.configure(text=f"Showing {n} months of data")

    # ── Chart renderer ────────────────────────────────────────────────────────

    def _render_trend(self, months: list[str], month_data: dict, now: datetime) -> None:
        ax = self._ax; fig = self._fig
        ax.clear(); ax.set_facecolor(SURFACE); fig.patch.set_facecolor(BG)

        cat_totals: dict[str, float] = defaultdict(float)
        for rows in month_data.values():
            for r in rows:
                cat = r.get("category_edited") or r.get("category", "Other")
                cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cats = sorted(cat_totals, key=lambda c: cat_totals[c], reverse=True)[:5]

        x_labels = [_short_month(m) for m in months]
        x        = list(range(len(months)))
        cat_palette = [CATEGORY_COLORS.get(c, "#89b4fa") for c in top_cats]

        for cat, color in zip(top_cats, cat_palette):
            y_vals = [
                sum(
                    (r.get("amount_edited") or r.get("amount") or 0)
                    for r in month_data[m]
                    if (r.get("category_edited") or r.get("category", "Other")) == cat
                )
                for m in months
            ]
            ax.plot(x, y_vals, marker="o", label=cat, color=color, linewidth=1.8)

        totals = [sum(r.get("amount_edited") or r.get("amount") or 0 for r in month_data[m]) for m in months]
        ax.plot(x, totals, marker="o", label="Total", color=TEXT, linewidth=2.5, linestyle="--", zorder=5)

        current = f"{now.year}-{now.month:02d}"
        if current in months:
            ax.axvline(months.index(current), color=ACCENT, linestyle=":", linewidth=1.5, alpha=0.8)

        ax.set_xticks(x); ax.set_xticklabels(x_labels, color=TEXT_DIM, fontsize=9)
        ax.tick_params(colors=TEXT_DIM)
        ax.set_ylabel("Amount (₹)", color=TEXT_DIM, fontsize=9)
        ax.set_title("Month-over-Month Spending", color=TEXT, fontsize=13, pad=12)
        ax.spines[:].set_color(BORDER)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=BORDER, linestyle="--", alpha=0.3)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=len(top_cats) + 1,
                  fontsize=8, facecolor=SURFACE, edgecolor=BORDER, labelcolor=TEXT)
        self._canv.draw()

    def _export_csv(self) -> None:
        from tkinter import filedialog
        if not self._trend_data:
            self._status_lbl.configure(text="No trend data — load trend first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="trend_comparison.csv",
        )
        if not path:
            return
        months = sorted(self._trend_data.keys())
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = _csv.writer(fh)
                writer.writerow(["month", "total", "count", "avg_transaction"])
                for m in months:
                    rows   = self._trend_data[m]
                    active = [r for r in rows if r.get("status") != "excluded"]
                    total  = sum(r.get("amount_edited") or r.get("amount") or 0 for r in active)
                    count  = len(active)
                    avg    = total / count if count else 0
                    writer.writerow([m, f"{total:.2f}", count, f"{avg:.2f}"])
            self._status_lbl.configure(text=f"Exported: {path}")
        except OSError as exc:
            self._status_lbl.configure(text=f"Export failed: {exc}")

    # ── Comparison table ──────────────────────────────────────────────────────

    def _render_table(self, months: list[str], month_data: dict) -> None:
        all_cat_totals: dict[str, float] = defaultdict(float)
        for rows in month_data.values():
            for r in rows:
                cat = r.get("category_edited") or r.get("category", "Other")
                all_cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
        top_cats = sorted(all_cat_totals, key=lambda c: all_cat_totals[c], reverse=True)[:4]

        col_names = ["Month", "Total"] + top_cats + ["Others", "vs Prev"]
        self._tree.configure(columns=col_names)
        for col in col_names:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=90, anchor="center")
        self._tree.column("Month", width=70)

        self._tree.delete(*self._tree.get_children())
        prev_total: float = 0
        for m in months:
            rows = month_data[m]
            total = sum(r.get("amount_edited") or r.get("amount") or 0 for r in rows)
            cat_totals: dict[str, float] = defaultdict(float)
            for r in rows:
                cat = r.get("category_edited") or r.get("category", "Other")
                cat_totals[cat] += r.get("amount_edited") or r.get("amount") or 0
            others = total - sum(cat_totals.get(c, 0) for c in top_cats)
            vs_prev = ""
            if prev_total > 0:
                pct = (total - prev_total) / prev_total * 100
                arrow = "↑" if pct >= 0 else "↓"
                vs_prev = f"{arrow} {abs(pct):.1f}%"
            values = (
                [_short_month(m), f"₹{total:,.0f}"]
                + [f"₹{cat_totals.get(c, 0):,.0f}" for c in top_cats]
                + [f"₹{others:,.0f}", vs_prev]
            )
            self._tree.insert("", "end", values=values)
            prev_total = total


# ── Helpers ───────────────────────────────────────────────────────────────────

def _short_month(month_str: str) -> str:
    try:
        return datetime.strptime(month_str, "%Y-%m").strftime("%b %y")
    except ValueError:
        return month_str
