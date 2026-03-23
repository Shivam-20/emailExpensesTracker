
"""
tabs/expenses_tab.py — Full expense table (ttk.Treeview) with toolbar,
category chips, amount filter, bulk actions, and inline editing.
"""

import csv
import logging
from tkinter import filedialog, messagebox, simpledialog
from typing import Callable, Optional

import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk

from config.category_map import ALL_CATEGORIES
from styles import (
    CATEGORY_COLORS, CONFIDENCE_COLORS, CONFIDENCE_BADGES,
    TEXT, TEXT_DIM, SURFACE, SURFACE_HOVER, SURFACE2,
    ACCENT, ACCENT_DARK, WARNING, ERROR, SUCCESS, AMBER, BORDER,
    BG, BORDER_BRIGHT, bind_tree_scroll
)

logger = logging.getLogger(__name__)

COLUMNS = [
    "Date", "Sender", "Subject", "Amount",
    "Currency", "Payment", "Category", "Tags", "Confidence", "Status",
]
COL_WIDTHS = {
    "Date": 90, "Sender": 180, "Subject": 280, "Amount": 90,
    "Currency": 70, "Payment": 120, "Category": 110,
    "Tags": 90, "Confidence": 80, "Status": 80,
}


class ExpensesTab:
    """Tab 1 — Expense table with filtering, inline editing, and bulk actions."""

    def __init__(self, parent, db=None) -> None:
        self._parent   = parent
        self._db       = db
        self._all_rows: list[dict] = []
        self._visible_rows: list[dict] = []
        self._active_categories: set[str] = set()
        self._chip_btns: dict[str, ctk.CTkButton] = {}
        self._selected_ids: set[str] = set()

        # Callbacks for MainWindow
        self.on_field_changed: Optional[Callable] = None
        self.on_exclude:       Optional[Callable] = None
        self.on_review:        Optional[Callable] = None

        self._setup_ui()

    def set_db(self, db) -> None:
        self._db = db

    # ── Public API ────────────────────────────────────────────────────────────

    def load_rows(self, rows: list[dict]) -> None:
        self._all_rows = rows
        self._active_categories.clear()
        self._rebuild_chips()
        self._apply_filters()

    def clear(self) -> None:
        self._all_rows = []
        self._visible_rows = []
        self._tree.delete(*self._tree.get_children())
        self._update_summary()

    def filter_by_category(self, cat: str) -> None:
        self._active_categories = {cat}
        self._rebuild_chips()
        self._apply_filters()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        frame = ctk.CTkFrame(self._parent, fg_color=BG, corner_radius=0)
        frame.pack(fill="both", expand=True)

        # ── Toolbar (search, amount filter, export) ───────────────────────
        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filters())
        search_entry = ctk.CTkEntry(
            toolbar, textvariable=self._search_var, width=260,
            placeholder_text="Search sender, subject, category, tag…",
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

        self._status_filter_var = ctk.StringVar(value="Active")
        ctk.CTkComboBox(
            toolbar,
            values=["All", "Active", "Excluded", "Review"],
            variable=self._status_filter_var,
            command=lambda _: self._apply_filters(),
            width=100, state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
            button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
            dropdown_hover_color=SURFACE_HOVER,
        ).pack(side="left", padx=(0, 8))

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
        self._chips_canvas = chips_canvas

        # ── Context menu ──────────────────────────────────────────────────
        self._ctx_menu = tk.Menu(frame._canvas if hasattr(frame, "_canvas") else frame._parent, tearoff=0,
                                  bg=SURFACE, fg=TEXT, activebackground=SURFACE_HOVER, activeforeground=TEXT,
                                  borderwidth=0, font=("Inter", 11))
        self._ctx_menu.add_command(label="Edit Amount…",   command=self._ctx_edit_amount)
        self._ctx_menu.add_command(label="Set Category…",  command=self._ctx_set_category)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="✓ Mark Active",    command=lambda: self._set_status_selected("active"))
        self._ctx_menu.add_command(label="🚫 Exclude",       command=lambda: self._set_status_selected("excluded"))
        self._ctx_menu.add_command(label="🔍 Mark for Review", command=lambda: self._set_status_selected("review"))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🔖 Add Tag…",     command=self._ctx_add_tag)
        self._ctx_menu.add_command(label="📋 Copy Row",     command=self._ctx_copy_row)

        # ── Treeview table ────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Expenses.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=28, font=("Inter", 11))
        style.configure("Expenses.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"),
                         relief="flat")
        style.map("Expenses.Treeview",
                  background=[("selected", ACCENT_DARK)],
                  foreground=[("selected", "#1e1e2e")])

        tree_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=8)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._tree = ttk.Treeview(
            tree_frame, style="Expenses.Treeview",
            columns=COLUMNS, show="headings",
            selectmode="extended",
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        for col in COLUMNS:
            self._tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=COL_WIDTHS[col], anchor="w",
                               minwidth=50, stretch=(col in ("Sender", "Subject")))

        bind_tree_scroll(self._tree)
        self._tree.bind("<Button-3>", self._on_right_click)
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        # Colour tags
        for cat, color in CATEGORY_COLORS.items():
            self._tree.tag_configure(f"cat_{cat}", foreground=color)
        self._tree.tag_configure("excluded", foreground=TEXT_DIM)
        self._tree.tag_configure("review",   foreground=AMBER)

        # ── Bulk action bar & summary ─────────────────────────────────────
        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(0, 6))

        self._bulk_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        self._bulk_frame.pack(side="left")

        for label, cmd in [
            ("✓ Active", lambda: self._bulk_set_status("active")),
            ("🚫 Exclude", lambda: self._bulk_set_status("excluded")),
            ("🔍 Review", lambda: self._bulk_set_status("review")),
        ]:
            ctk.CTkButton(self._bulk_frame, text=label, command=cmd,
                           font=ctk.CTkFont(family="Inter", size=11),
                           fg_color="transparent", hover_color=SURFACE_HOVER, text_color=TEXT_DIM,
                           border_color=BORDER, border_width=1, corner_radius=6, height=26, width=90,
                           ).pack(side="left", padx=(0, 6))

        self._summary_lbl = ctk.CTkLabel(
            bottom, text="", text_color=TEXT_DIM,
            font=ctk.CTkFont(family="Inter", size=11),
        )
        self._summary_lbl.pack(side="right")

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

    def _update_all_chip_state(self) -> None:
        self._active_categories.clear()
        self._rebuild_chips()

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        query  = self._search_var.get().lower().strip()
        status = self._status_filter_var.get()
        cats   = self._active_categories

        try:    min_amt = float(self._min_amt_var.get())
        except (ValueError, TypeError): min_amt = None
        try:    max_amt = float(self._max_amt_var.get())
        except (ValueError, TypeError): max_amt = None

        def _keep(r: dict) -> bool:
            st = r.get("status", "active") or "active"
            if status == "Active"   and st == "excluded":  return False
            if status == "Excluded" and st != "excluded":  return False
            if status == "Review"   and st != "review":    return False

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
            cat    = row.get("category_edited") or row.get("category", "Other")
            amt    = row.get("amount_edited") or row.get("amount") or 0
            sym    = sym_map.get(row.get("currency", "INR"), "")
            st     = row.get("status", "active") or "active"
            conf   = row.get("confidence", "") or ""
            iid    = row.get("id", "")
            tags   = (row.get("tags") or "").strip()

            vals = [
                (row.get("email_date") or "")[:10],
                _trunc(row.get("sender") or row.get("sender_email") or "", 30),
                _trunc(row.get("subject", ""), 55),
                f"{sym}{amt:,.2f}",
                row.get("currency", "INR"),
                _trunc(row.get("payment_method", ""), 20),
                cat,
                tags[:12] if tags else "",
                conf,
                st,
            ]

            tag = "excluded" if st == "excluded" else ("review" if st == "review" else f"cat_{cat}")
            self._tree.insert("", "end", iid=iid, values=vals, tags=(tag,))

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
            if col == "Status":
                return r.get("status", "") or ""
            return ""
        self._visible_rows.sort(key=_key, reverse=not self._sort_asc)

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self, event) -> None:
        self._selected_ids = set(self._tree.selection())

    def _get_focused_row(self) -> Optional[dict]:
        item = self._tree.focus()
        return next((r for r in self._visible_rows if r.get("id") == item), None)

    # ── Context menu ──────────────────────────────────────────────────────────

    def _on_right_click(self, event) -> None:
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.focus(row)
            self._tree.selection_set(row)
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _ctx_edit_amount(self) -> None:
        row = self._get_focused_row()
        if not row:
            return
        dlg = _EditAmountDialog(self._tree, row)
        if dlg.result is not None:
            self._persist_field(row["id"], "amount_edited", dlg.result)
            row["amount_edited"] = dlg.result
            self._populate_table()

    def _ctx_set_category(self) -> None:
        row = self._get_focused_row()
        if not row:
            return
        dlg = _SetCategoryDialog(self._tree, row)
        if dlg.result:
            self._persist_field(row["id"], "category_edited", dlg.result)
            row["category_edited"] = dlg.result
            self._rebuild_chips()
            self._populate_table()

    def _ctx_add_tag(self) -> None:
        row = self._get_focused_row()
        if not row:
            return
        tag = simpledialog.askstring("Add Tag", "Tag:", parent=self._tree)
        if tag:
            existing = (row.get("tags") or "").strip()
            new_tags = (existing + " " + tag.strip()).strip() if existing else tag.strip()
            self._persist_field(row["id"], "tags", new_tags)
            row["tags"] = new_tags
            self._populate_table()

    def _ctx_copy_row(self) -> None:
        row = self._get_focused_row()
        if not row:
            return
        text = " | ".join(str(v) for v in [
            (row.get("email_date") or "")[:10],
            row.get("sender", ""),
            row.get("subject", ""),
            row.get("amount_edited") or row.get("amount") or 0,
            row.get("currency", "INR"),
            row.get("category_edited") or row.get("category", "Other"),
        ])
        self._tree.clipboard_clear()
        self._tree.clipboard_append(text)

    def _set_status_selected(self, status: str) -> None:
        item = self._tree.focus()
        if not item:
            return
        row = next((r for r in self._visible_rows if r.get("id") == item), None)
        if row:
            self._persist_field(row["id"], "status", status)
            row["status"] = status
            if status == "excluded" and self.on_exclude:
                self.on_exclude(row["id"], row.get("sender_email", row.get("sender", "")))
            elif status == "review" and self.on_review:
                self.on_review(row["id"])
            self._apply_filters()

    # ── Double-click inline edit ──────────────────────────────────────────────

    def _on_double_click(self, event) -> None:
        row  = self._tree.identify_row(event.y)
        col  = self._tree.identify_column(event.x)
        if not row or not col:
            return
        col_idx = int(col[1:]) - 1
        col_name = COLUMNS[col_idx] if col_idx < len(COLUMNS) else ""
        data_row = next((r for r in self._visible_rows if r.get("id") == row), None)
        if not data_row:
            return
        if col_name == "Amount":
            self._ctx_edit_amount()
        elif col_name == "Category":
            self._ctx_set_category()
        elif col_name == "Status":
            self._ctx_cycle_status(data_row)
        elif col_name == "Tags":
            self._ctx_add_tag()

    def _ctx_cycle_status(self, row: dict) -> None:
        cycle = {"active": "excluded", "excluded": "review", "review": "active"}
        curr  = row.get("status", "active") or "active"
        new_status = cycle.get(curr, "active")
        self._persist_field(row["id"], "status", new_status)
        row["status"] = new_status
        if new_status == "review" and self.on_review:
            self.on_review(row["id"])
        self._apply_filters()

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def _bulk_set_status(self, status: str) -> None:
        selected = list(self._tree.selection())
        if not selected:
            messagebox.showinfo("No Selection", "Select rows first (Shift-click or Ctrl-click).")
            return
        for iid in selected:
            rr = next((r for r in self._visible_rows if r.get("id") == iid), None)
            if rr:
                self._persist_field(rr["id"], "status", status)
                rr["status"] = status
        self._apply_filters()

    # ── Persist ───────────────────────────────────────────────────────────────

    def _persist_field(self, msg_id: str, field: str, value) -> None:
        if self.on_field_changed:
            self.on_field_changed(msg_id, field, value)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="expenses.csv",
        )
        if not path:
            return
        rows = self._visible_rows
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(COLUMNS)
                sym_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
                for row in rows:
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
                        row.get("tags", ""),
                        row.get("confidence", ""),
                        row.get("status", "active"),
                    ])
            messagebox.showinfo("Exported", f"Exported {len(rows)} rows to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ── Summary ───────────────────────────────────────────────────────────────

    def _update_summary(self) -> None:
        active = [r for r in self._visible_rows if r.get("status") != "excluded"]
        total  = sum(r.get("amount_edited") or r.get("amount") or 0 for r in active)
        sym_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
        currencies = [r.get("currency", "INR") for r in active]
        sym = sym_map.get(max(set(currencies), key=currencies.count), "") if currencies else "₹"
        self._summary_lbl.configure(
            text=f"{len(self._visible_rows)} rows • {len(active)} active • {sym}{total:,.2f}"
        )


# ── Helper dialogs ────────────────────────────────────────────────────────────

class _EditAmountDialog(ctk.CTkToplevel):
    def __init__(self, parent, row: dict) -> None:
        super().__init__(parent)
        self.title("Edit Amount")
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[float] = None
        self.configure(fg_color=BG)

        curr = row.get("amount_edited") or row.get("amount") or 0
        ctk.CTkLabel(self, text=f"Amount for: {_trunc(row.get('subject',''), 40)}",
                      text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11)).pack(pady=(12, 4))
        self._entry = ctk.CTkEntry(self, width=160, font=ctk.CTkFont(family="Inter", size=13),
                                    fg_color=SURFACE, border_color=BORDER, text_color=TEXT)
        self._entry.insert(0, str(curr))
        self._entry.select_range(0, "end")
        self._entry.pack(pady=4)
        self._entry.focus()
        self._entry.bind("<Return>", lambda e: self._save())

        row_btns = ctk.CTkFrame(self, fg_color="transparent")
        row_btns.pack(pady=8)
        ctk.CTkButton(row_btns, text="Save", command=self._save,
                       fg_color=ACCENT, text_color="#1e1e2e", corner_radius=8, width=80).pack(side="left", padx=6)
        ctk.CTkButton(row_btns, text="Cancel", command=self.destroy,
                       fg_color="transparent", text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                       corner_radius=8, width=80).pack(side="left")
        self.wait_window(self)

    def _save(self) -> None:
        try:
            self.result = float(self._entry.get())
        except ValueError:
            pass
        self.destroy()


class _SetCategoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, row: dict) -> None:
        super().__init__(parent)
        self.title("Set Category")
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None
        self.configure(fg_color=BG)

        ctk.CTkLabel(self, text=f"Category for: {_trunc(row.get('subject',''), 40)}",
                      text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11)).pack(pady=(12, 4))

        self._var = ctk.StringVar(value=row.get("category_edited") or row.get("category", "Other"))
        ctk.CTkComboBox(self, values=ALL_CATEGORIES, variable=self._var, state="readonly", width=200,
                         font=ctk.CTkFont(family="Inter", size=12),
                         fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                         button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                         dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                         dropdown_hover_color=SURFACE_HOVER,
                         ).pack(pady=4)

        row_btns = ctk.CTkFrame(self, fg_color="transparent")
        row_btns.pack(pady=8)
        ctk.CTkButton(row_btns, text="Save", command=self._save,
                       fg_color=ACCENT, text_color="#1e1e2e", corner_radius=8, width=80).pack(side="left", padx=6)
        ctk.CTkButton(row_btns, text="Cancel", command=self.destroy,
                       fg_color="transparent", text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                       corner_radius=8, width=80).pack(side="left")
        self.wait_window(self)

    def _save(self) -> None:
        self.result = self._var.get()
        self.destroy()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trunc(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"
