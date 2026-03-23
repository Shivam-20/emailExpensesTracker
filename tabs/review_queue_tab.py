"""
tabs/review_queue_tab.py — Extended Review Queue matching expenses_tab features.
Allows search, filtering, sorting, CSV export, and provides inline double-click correction
panels for ML feedback.
"""

import csv
import logging
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk

from config.category_map import ALL_CATEGORIES
from styles import (
    CATEGORY_COLORS, TEXT, TEXT_DIM, SURFACE, SURFACE_HOVER,
    ACCENT, ACCENT_DARK, WARNING, ERROR, SUCCESS, AMBER, BORDER,
    BG, BORDER_BRIGHT, bind_tree_scroll,
)

logger = logging.getLogger(__name__)

COLUMNS = [
    "Date", "Sender", "Subject", "Amount",
    "Currency", "Payment", "Category", "Confidence",
]
COL_WIDTHS = {
    "Date": 90, "Sender": 180, "Subject": 280, "Amount": 90,
    "Currency": 70, "Payment": 120, "Category": 110, "Confidence": 80,
}


class ReviewQueueTab:
    """Tab 4 — Review queue full rewrite with expenses_tab filtering + correction panel."""

    def __init__(self, parent, db=None) -> None:
        self._parent = parent
        self._db     = db
        self._all_rows: list[dict] = []
        self._visible_rows: list[dict] = []
        self._active_categories: set[str] = set()
        self._chip_btns: dict[str, ctk.CTkButton] = {}
        self._selected_ids: set[str] = set()
        
        # Callbacks (set by MainWindow)
        self.on_corrected: Optional[Callable] = None

        self._editing_row_id: Optional[str] = None
        self._setup_ui()

    def set_db(self, db, data_dir=None) -> None:
        self._db = db
        self._data_dir = data_dir

    def get_review_count(self) -> int:
        return len(self._all_rows)

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload review-queue rows from the database."""
        if not self._db:
            return
        try:
            months = self._db.get_available_months()
            all_rows = []
            for month in months:
                rows = self._db.get_month_expenses(month)
                all_rows.extend(dict(r) for r in rows)
            self.load_rows(all_rows)
        except Exception as exc:
            logger.warning("Failed to refresh review queue: %s", exc)

    def load_rows(self, rows: list[dict]) -> None:
        self._all_rows = []
        for r in rows:
            st = r.get("status", "active") or "active"
            if st == "review":
                self._all_rows.append(r)
        
        self._active_categories.clear()
        self._rebuild_chips()
        self._apply_filters()
        self._hide_action_panel()

    def clear(self) -> None:
        self._all_rows = []
        self._visible_rows = []
        self._tree.delete(*self._tree.get_children())
        self._update_summary()
        self._hide_action_panel()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        frame = ctk.CTkFrame(self._parent, fg_color=BG, corner_radius=0)
        frame.pack(fill="both", expand=True)

        # ── Toolbar (Search, amounts, export) ─────────────────────────────
        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filters())
        search_entry = ctk.CTkEntry(
            toolbar, textvariable=self._search_var, width=260,
            placeholder_text="Search review queue…",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
        )
        search_entry.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(toolbar, text="≥₹", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left")
        self._min_amt_var = ctk.StringVar(value="")
        self._min_amt_var.trace_add("write", lambda *_: self._apply_filters())
        ctk.CTkEntry(toolbar, textvariable=self._min_amt_var, width=70,
                      placeholder_text="min",
                      font=ctk.CTkFont(family="Inter", size=12),
                      fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
                      ).pack(side="left", padx=(2, 4))

        ctk.CTkLabel(toolbar, text="≤₹", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left")
        self._max_amt_var = ctk.StringVar(value="")
        self._max_amt_var.trace_add("write", lambda *_: self._apply_filters())
        ctk.CTkEntry(toolbar, textvariable=self._max_amt_var, width=70,
                      placeholder_text="max",
                      font=ctk.CTkFont(family="Inter", size=12),
                      fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
                      ).pack(side="left", padx=(2, 8))

        ctk.CTkButton(toolbar, text="📥 Export CSV", command=self._export_csv,
                       font=ctk.CTkFont(family="Inter", size=11),
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT_DARK, border_width=1, corner_radius=6, height=28,
                       ).pack(side="right")

        # ── Category chips ────────────────────────────────────────────────
        chips_wrapper = ctk.CTkFrame(frame, fg_color="transparent", height=36)
        chips_wrapper.pack(fill="x", padx=8, pady=(0, 4))
        chips_wrapper.pack_propagate(False)

        chips_canvas = tk.Canvas(chips_wrapper, bg=BG, height=34, highlightthickness=0)
        chips_canvas.pack(fill="x", expand=True, side="left")
        self._chips_inner = ctk.CTkFrame(chips_canvas, fg_color="transparent")
        self._chips_window = chips_canvas.create_window((0, 0), window=self._chips_inner, anchor="nw")
        chips_canvas.bind("<Configure>", lambda e: chips_canvas.configure(scrollregion=chips_canvas.bbox("all")))
        chips_canvas.bind("<MouseWheel>", lambda e: chips_canvas.xview_scroll(-1 * int(e.delta / 120), "units"))
        
        # ── Context Menu ──────────────────────────────────────────────────
        self._ctx_menu = tk.Menu(frame._canvas if hasattr(frame, "_canvas") else frame._parent, tearoff=0,
                                  bg=SURFACE, fg=TEXT, activebackground=SURFACE_HOVER, activeforeground=TEXT,
                                  borderwidth=0, font=("Inter", 11))
        self._ctx_menu.add_command(label="📝 Correct & Categorize", command=self._open_action_panel_for_selected)

        # ── Treeview table ────────────────────────────────────────────────
        style = ttk.Style()
        style.configure("Review.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=28, font=("Inter", 11))
        style.configure("Review.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"),
                         relief="flat")
        style.map("Review.Treeview",
                  background=[("selected", ACCENT_DARK)],
                  foreground=[("selected", "#1e1e2e")])

        tree_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=8)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._tree = ttk.Treeview(
            tree_frame, style="Review.Treeview",
            columns=COLUMNS, show="headings",
            selectmode="extended",
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)
        bind_tree_scroll(self._tree)

        for col in COLUMNS:
            self._tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=COL_WIDTHS[col], anchor="w",
                               minwidth=50, stretch=(col in ("Sender", "Subject")))

        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-3>", self._on_right_click)

        self._tree.tag_configure("review", foreground=AMBER)

        # ── Bottom layout ─────────────────────────────────────────────────
        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(0, 6))
        
        self._summary_lbl = ctk.CTkLabel(bottom, text="", text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11))
        self._summary_lbl.pack(side="right")

        # ── Action Panel ──────────────────────────────────────────────────
        self._action_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=10, border_color=BORDER, border_width=1)
        # Packed lazily upon double click

        hdr_row = ctk.CTkFrame(self._action_frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(hdr_row, text="📝 Resolve Classification", font=ctk.CTkFont(family="Inter", size=13, weight="bold")).pack(side="left")
        self._action_subject_lbl = ctk.CTkLabel(hdr_row, text="", text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11, slant="italic"))
        self._action_subject_lbl.pack(side="left", padx=16)

        form_row = ctk.CTkFrame(self._action_frame, fg_color="transparent")
        form_row.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(form_row, text="Label:", width=50, anchor="e").pack(side="left")
        self._label_combo = ctk.CTkComboBox(form_row, values=["EXPENSE", "NOT_EXPENSE"], width=130, state="readonly", font=ctk.CTkFont(family="Inter", size=12))
        self._label_combo.pack(side="left", padx=(6, 20))
        self._label_combo.set("EXPENSE")

        ctk.CTkLabel(form_row, text="Category:", width=70, anchor="e").pack(side="left")
        self._cat_combo = ctk.CTkComboBox(form_row, values=ALL_CATEGORIES, width=160, state="readonly", font=ctk.CTkFont(family="Inter", size=12))
        self._cat_combo.pack(side="left", padx=(6, 20))

        btns_row = ctk.CTkFrame(self._action_frame, fg_color="transparent")
        btns_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(btns_row, text="Save Correction", command=self._save_correction, fg_color=ACCENT, text_color="#1e1e2e", font=ctk.CTkFont(family="Inter", size=12, weight="bold"), width=120, height=28).pack(side="left")
        ctk.CTkButton(btns_row, text="Cancel", command=self._hide_action_panel, fg_color="transparent", text_color=TEXT_DIM, hover_color=SURFACE_HOVER, width=70, height=28).pack(side="left", padx=10)

        # Sort state
        self._sort_col: Optional[str] = None
        self._sort_asc: bool = True

    # ── Chip rebuild ──────────────────────────────────────────────────────────

    def _rebuild_chips(self) -> None:
        for widget in self._chips_inner.winfo_children():
            widget.destroy()
        self._chip_btns.clear()

        cats_in_data = sorted({
            r.get("category_edited") or r.get("category", "Other")
            for r in self._all_rows
        })

        def _make_chip(cat: str) -> None:
            color  = CATEGORY_COLORS.get(cat, "#6c7086")
            active = cat in self._active_categories
            fg     = "#1e1e2e" if active else color
            bg     = color     if active else "transparent"
            btn = ctk.CTkButton(
                self._chips_inner, text=cat,
                command=lambda c=cat: self._toggle_chip(c),
                font=ctk.CTkFont(family="Inter", size=10),
                fg_color=bg, hover_color=color, text_color=fg,
                border_color=color, border_width=1, corner_radius=999,
                height=22, width=max(60, len(cat) * 8),
            )
            btn.pack(side="left", padx=3)
            self._chip_btns[cat] = btn

        for cat in cats_in_data:
            _make_chip(cat)
        self._chips_inner.update_idletasks()

    def _toggle_chip(self, cat: str) -> None:
        if cat in self._active_categories:
            self._active_categories.discard(cat)
        else:
            self._active_categories.add(cat)
        self._rebuild_chips()
        self._apply_filters()

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        query = self._search_var.get().lower().strip()
        cats  = self._active_categories

        try:    min_amt = float(self._min_amt_var.get())
        except (ValueError, TypeError): min_amt = None
        try:    max_amt = float(self._max_amt_var.get())
        except (ValueError, TypeError): max_amt = None

        def _keep(r: dict) -> bool:
            cat = r.get("category_edited") or r.get("category", "Other")
            if cats and cat not in cats:
                return False

            amt = r.get("amount_edited") or r.get("amount") or 0
            if min_amt is not None and amt < min_amt: return False
            if max_amt is not None and amt > max_amt: return False

            if query:
                haystack = " ".join(str(v) for v in [
                    r.get("sender", ""), r.get("sender_email", ""),
                    r.get("subject", ""), cat,
                    r.get("tags", ""), r.get("payment_method", ""),
                ]).lower()
                if query not in haystack:
                    return False
            return True

        self._visible_rows = [r for r in self._all_rows if _keep(r)]
        if self._sort_col:
            self._sort_rows()
        self._populate_table()
        self._update_summary()

    def _populate_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        sym_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
        for row in self._visible_rows:
            cat  = row.get("category_edited") or row.get("category", "Other")
            amt  = row.get("amount_edited") or row.get("amount") or 0
            sym  = sym_map.get(row.get("currency", "INR"), "")
            conf = row.get("confidence", "") or ""
            iid  = row.get("id", "")

            vals = [
                (row.get("email_date") or "")[:10],
                self._trunc(row.get("sender") or row.get("sender_email") or "", 30),
                self._trunc(row.get("subject", ""), 55),
                f"{sym}{amt:,.2f}",
                row.get("currency", "INR"),
                self._trunc(row.get("payment_method", ""), 20),
                cat,
                conf,
            ]
            self._tree.insert("", "end", iid=iid, values=vals, tags=("review",))

    # ── Sort ──────────────────────────────────────────────────────────────────

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._sort_rows()
        self._populate_table()

    def _sort_rows(self) -> None:
        col = self._sort_col
        def _key(r: dict):
            if col == "Amount":
                return r.get("amount_edited") or r.get("amount") or 0
            if col == "Date":
                return r.get("email_date", "") or ""
            if col == "Category":
                return r.get("category_edited") or r.get("category", "Other")
            if col == "Sender":
                return r.get("sender", "") or ""
            return ""
        self._visible_rows.sort(key=_key, reverse=not self._sort_asc)

    # ── Interaction ───────────────────────────────────────────────────────────

    def _on_right_click(self, event) -> None:
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.focus(row)
            self._tree.selection_set(row)
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _on_double_click(self, event) -> None:
        self._open_action_panel_for_selected()

    def _open_action_panel_for_selected(self) -> None:
        item = self._tree.focus()
        if not item:
            return
        row = next((r for r in self._visible_rows if r.get("id") == item), None)
        if not row:
            return

        self._editing_row_id = item
        subj = self._trunc(row.get("subject", ""), 60)
        self._action_subject_lbl.configure(text=f"“{subj}”")
        
        cat = row.get("category_edited") or row.get("category", "Other")
        if cat in ALL_CATEGORIES:
            self._cat_combo.set(cat)
        else:
            self._cat_combo.set("Other")
            
        self._label_combo.set("EXPENSE")

        self._action_frame.pack(fill="x", padx=8, pady=(0, 6), side="bottom")

    def _hide_action_panel(self) -> None:
        self._editing_row_id = None
        self._action_frame.pack_forget()

    def _save_correction(self) -> None:
        if not self._editing_row_id or not self._db:
            return

        row = next((r for r in self._all_rows if r.get("id") == self._editing_row_id), None)
        if not row:
            return

        lbl = self._label_combo.get()
        cat = self._cat_combo.get()
        
        self._db.upsert_human_correction(
            msg_id=row["id"],
            subject=row.get("subject", ""),
            sender=row.get("sender_email", ""),
            true_label=lbl,
            true_category=cat if lbl == "EXPENSE" else None
        )
        
        new_status = "active" if lbl == "EXPENSE" else "excluded"
        self._db.set_expense_status(row["id"], new_status)
        
        if lbl == "EXPENSE":
            self._db.set_expense_category(row["id"], cat)
            row["category_edited"] = cat
            row["status"] = "active"
        else:
            row["status"] = "excluded"

        if self.on_corrected:
            self.on_corrected(row["id"], new_status)

        self._hide_action_panel()
        
        self._all_rows = [r for r in self._all_rows if r["id"] != row["id"]]
        self._rebuild_chips()
        self._apply_filters()

    # ── Export & Summary ──────────────────────────────────────────────────────
        
    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="review_queue.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(COLUMNS)
                sym_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
                for row in self._visible_rows:
                    cat = row.get("category_edited") or row.get("category", "Other")
                    amt = row.get("amount_edited") or row.get("amount") or 0
                    sym = sym_map.get(row.get("currency", "INR"), "")
                    writer.writerow([
                        (row.get("email_date") or "")[:10],
                        row.get("sender", ""),
                        row.get("subject", ""),
                        f"{sym}{amt:,.2f}",
                        row.get("currency", "INR"),
                        row.get("payment_method", ""),
                        cat,
                        row.get("confidence", ""),
                    ])
            messagebox.showinfo("Exported", f"Exported {len(self._visible_rows)} reviews to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _update_summary(self) -> None:
        self._summary_lbl.configure(text=f"{len(self._visible_rows)} items in review queue")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _trunc(self, text: str, n: int) -> str:
        return text if len(text) <= n else text[:n - 1] + "…"
