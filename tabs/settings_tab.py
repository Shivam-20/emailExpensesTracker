
"""
tabs/settings_tab.py — Budgets, Ignore List, Custom Rules, Data Management, Model Training.
"""

import json
import logging
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk
import tkinter.ttk as ttk

from config.category_map import ALL_CATEGORIES
from styles import (
    ACCENT, ACCENT_DARK, ACCENT_LIGHT, BORDER, ERROR, SUCCESS, WARNING,
    SURFACE, SURFACE_HOVER, TEXT, TEXT_DIM, BG, bind_tree_scroll
)

logger = logging.getLogger(__name__)


class SettingsTab:
    """Tab 5 — Budgets, Ignore List, Custom Rules, Data Management, Model Training."""

    # Callbacks (set by MainWindow before first use)
    on_reauth:            Optional[Callable] = None
    on_clear_cache:       Optional[Callable] = None
    on_data_dir_changed:  Optional[Callable] = None
    on_backend_changed:   Optional[Callable] = None
    on_training_finished: Optional[Callable] = None

    def __init__(self, parent) -> None:
        self._parent        = parent
        self._db            = None
        self._data_dir: Optional[Path] = None
        self._config: dict  = {}
        self._training_worker = None
        self._setup_ui()

    def set_db(self, db, data_dir: Path, config: dict) -> None:
        self._db       = db
        self._data_dir = data_dir
        self._config   = config
        self._load_all()

    def refresh(self) -> None:
        self._load_budgets()

    def get_custom_rules(self) -> list[dict]:
        return self._config.get("custom_rules", [])

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = ctk.CTkScrollableFrame(self._parent, fg_color=BG, corner_radius=0,
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=ACCENT_DARK)
        outer.pack(fill="both", expand=True)
        self._scroll = outer

        def _section(title: str) -> ctk.CTkFrame:
            f = ctk.CTkFrame(outer, fg_color=SURFACE, corner_radius=10,
                              border_color=BORDER, border_width=1)
            f.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(f, text=title,
                          font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                          text_color=TEXT, anchor="w").pack(fill="x", padx=12, pady=(10, 6))
            _div(f)
            return f

        self._build_budgets_section(_section("📊 Budget vs Actual"))
        self._build_ignore_section(_section("🚫 Ignore List"))
        self._build_rules_section(_section("⚙️ Custom Keyword Rules"))
        self._build_ai_backend_section(_section("🤖 Stage 3 AI Backend"))
        self._build_training_section(_section("🧠 Model Training"))
        self._build_data_section(_section("🗄️ Data Management"))

    # ── Budget section ────────────────────────────────────────────────────────

    def _build_budgets_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        style = ttk.Style()
        style.configure("Budget.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=26, font=("Inter", 10))
        style.configure("Budget.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"))
        style.map("Budget.Treeview", background=[("selected", "#313244")])

        cols = ["category", "budget", "spent", "pct", "status"]
        heads = ["Category", "Budget (₹)", "Spent (₹)", "%", "Status"]

        self._budget_tree = ttk.Treeview(inner, style="Budget.Treeview",
                                          columns=cols, show="headings", height=8, selectmode="browse")
        vsb = ttk.Scrollbar(inner, orient="vertical", command=self._budget_tree.yview)
        self._budget_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._budget_tree.pack(fill="x")
        bind_tree_scroll(self._budget_tree)

        widths = {"category": 130, "budget": 100, "spent": 100, "pct": 70, "status": 80}
        for cid, chead in zip(cols, heads):
            self._budget_tree.heading(cid, text=chead)
            self._budget_tree.column(cid, width=widths[cid], anchor="center" if cid != "category" else "w")

        self._budget_tree.bind("<Double-1>", self._on_budget_double_click)

        ctk.CTkLabel(inner, text="Double-click a row to set a budget.", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=10)).pack(anchor="w", pady=(4, 0))

    def _load_budgets(self) -> None:
        if not self._db:
            return
        budgets = self._db.get_budgets()
        spent_map: dict[str, float] = {}
        try:
            months = self._db.get_available_months()
            if months:
                rows = self._db.get_month_expenses(months[-1])
                for r in rows:
                    if r["status"] == "excluded":
                        continue
                    cat = r["category_edited"] or r["category"] or "Other"
                    spent_map[cat] = spent_map.get(cat, 0) + (r["amount_edited"] or r["amount"] or 0)
        except Exception:
            pass

        self._budget_tree.delete(*self._budget_tree.get_children())
        for cat in ALL_CATEGORIES:
            budget = budgets.get(cat, 0.0)
            spent  = spent_map.get(cat, 0.0)
            pct    = (spent / budget * 100) if budget > 0 else 0
            over   = budget > 0 and spent > budget
            status = "⚠ Over" if over else ("OK" if budget > 0 else "—")
            tag    = "over" if over else ("ok" if budget > 0 else "none")
            self._budget_tree.insert("", "end", iid=cat, tags=(tag,),
                                      values=[cat, f"₹{budget:,.0f}", f"₹{spent:,.0f}",
                                              f"{pct:.0f}%", status])
        self._budget_tree.tag_configure("over", foreground=ERROR)
        self._budget_tree.tag_configure("ok",   foreground=SUCCESS)

    def _on_budget_double_click(self, event) -> None:
        item = self._budget_tree.focus()
        if not item:
            return
        cat = self._budget_tree.item(item, "values")[0]
        dlg = _BudgetDialog(self._scroll, cat)
        new_val = dlg.result
        if new_val is not None and self._db:
            self._db.set_budget(cat, new_val)
            self._load_budgets()

    # ── Ignore list section ───────────────────────────────────────────────────

    def _build_ignore_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        style = ttk.Style()
        style.configure("Ignore.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=24, font=("Inter", 10))
        style.configure("Ignore.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"))
        style.map("Ignore.Treeview", background=[("selected", "#313244")])

        cols = ["itype", "ivalue", "created"]
        heads = ["Type", "Value", "Added On"]
        self._ignore_tree = ttk.Treeview(inner, style="Ignore.Treeview",
                                          columns=cols, show="headings", height=5, selectmode="browse")
        vsb = ttk.Scrollbar(inner, orient="vertical", command=self._ignore_tree.yview)
        self._ignore_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._ignore_tree.pack(fill="x")
        bind_tree_scroll(self._ignore_tree)

        for cid, chead, w in zip(cols, heads, [80, 300, 90]):
            self._ignore_tree.heading(cid, text=chead)
            self._ignore_tree.column(cid, width=w, anchor="w")

        ctk.CTkButton(inner, text="🗑 Remove Selected", command=self._remove_selected_ignore,
                       font=ctk.CTkFont(family="Inter", size=11),
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ERROR,
                       border_color=ERROR, border_width=1, corner_radius=6, height=26).pack(anchor="w", pady=(6, 0))

    def _load_ignore_list(self) -> None:
        if not self._db:
            return
        rows = self._db.get_ignore_list()
        self._ignore_tree.delete(*self._ignore_tree.get_children())
        for row in rows:
            self._ignore_tree.insert("", "end", iid=str(row["id"]),
                                      values=[row["type"], row["value"], str(row["created_at"])[:10]])

    def _remove_selected_ignore(self) -> None:
        item = self._ignore_tree.focus()
        if not item or not self._db:
            return
        self._db.remove_ignore(int(item))
        self._load_ignore_list()

    # ── Custom rules section ──────────────────────────────────────────────────

    def _build_rules_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        style = ttk.Style()
        style.configure("Rules.Treeview",
                         background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                         rowheight=24, font=("Inter", 10))
        style.configure("Rules.Treeview.Heading",
                         background="#16162a", foreground=TEXT_DIM, font=("Inter", 10, "bold"))
        style.map("Rules.Treeview", background=[("selected", "#313244")])

        cols = ["keyword", "match_in", "category"]
        heads = ["Keyword", "Matches In", "Category"]
        self._rules_tree = ttk.Treeview(inner, style="Rules.Treeview",
                                         columns=cols, show="headings", height=4, selectmode="browse")
        vsb = ttk.Scrollbar(inner, orient="vertical", command=self._rules_tree.yview)
        self._rules_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._rules_tree.pack(fill="x")
        bind_tree_scroll(self._rules_tree)

        for cid, chead, w in zip(cols, heads, [200, 100, 120]):
            self._rules_tree.heading(cid, text=chead)
            self._rules_tree.column(cid, width=w, anchor="w")

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(btn_row, text="+ Add Rule", command=self._add_rule,
                       font=ctk.CTkFont(family="Inter", size=11),
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT, border_width=1, corner_radius=6, height=26).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="🗑 Delete Selected", command=self._delete_selected_rule,
                       font=ctk.CTkFont(family="Inter", size=11),
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ERROR,
                       border_color=ERROR, border_width=1, corner_radius=6, height=26).pack(side="left")

    def _load_rules(self) -> None:
        rules = self._config.get("custom_rules", [])
        self._rules_tree.delete(*self._rules_tree.get_children())
        for i, rule in enumerate(rules):
            self._rules_tree.insert("", "end", iid=str(i),
                                     values=[rule.get("keyword", ""), rule.get("match_in", "both"),
                                             rule.get("category", "Other")])

    def _add_rule(self) -> None:
        dlg = _AddRuleDialog(self._scroll)
        rule = dlg.result
        if rule:
            rules = self._config.setdefault("custom_rules", [])
            rules.append(rule)
            self._save_config()
            self._load_rules()

    def _delete_selected_rule(self) -> None:
        item = self._rules_tree.focus()
        if not item:
            return
        idx = int(item)
        rules = self._config.get("custom_rules", [])
        if 0 <= idx < len(rules):
            rules.pop(idx)
            self._save_config()
            self._load_rules()

    # ── AI Backend section ────────────────────────────────────────────────────

    def _build_ai_backend_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(inner, text="Controls which AI model handles ambiguous emails after rules + ML.",
                      text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11),
                      wraplength=600, justify="left", anchor="w").pack(fill="x", pady=(0, 8))

        self._backend_var = ctk.StringVar(value="distilbert")
        ctk.CTkRadioButton(
            inner, text="DistilBERT  (faster · CPU-only · ~200 ms/email · no Ollama needed)",
            variable=self._backend_var, value="distilbert", command=self._on_backend_changed,
            font=ctk.CTkFont(family="Inter", size=12), text_color=TEXT,
            fg_color=ACCENT, hover_color=ACCENT_DARK, border_color=BORDER,
        ).pack(anchor="w", pady=3)

        ctk.CTkRadioButton(
            inner, text="phi4-mini via Ollama  (zero-shot · better for ambiguous · requires Ollama)",
            variable=self._backend_var, value="phi4-mini", command=self._on_backend_changed,
            font=ctk.CTkFont(family="Inter", size=12), text_color=TEXT,
            fg_color=ACCENT, hover_color=ACCENT_DARK, border_color=BORDER,
        ).pack(anchor="w", pady=3)

    def _load_ai_backend(self) -> None:
        try:
            from classifier.config import _load_stage3_backend
            backend = _load_stage3_backend()
        except Exception:
            backend = "distilbert"
        self._backend_var.set(backend)

    def _on_backend_changed(self) -> None:
        backend = self._backend_var.get()
        try:
            from classifier.config import save_stage3_backend
            save_stage3_backend(backend)
        except Exception as exc:
            logger.error("Could not save Stage 3 backend: %s", exc)
            return
        if backend == "phi4-mini":
            import urllib.request
            try:
                urllib.request.urlopen("http://localhost:11434", timeout=2)
            except Exception:
                messagebox.showwarning(
                    "Ollama Not Running",
                    "phi4-mini requires Ollama to be running.\n\n"
                    "Install: https://ollama.com\nStart: ollama serve\nPull: ollama pull phi4-mini\n\n"
                    "Stage 3 will fall back to REVIEW until Ollama is available.",
                )
        if self.on_backend_changed:
            self.on_backend_changed(backend)

    # ── Model Training section ────────────────────────────────────────────────

    def _build_training_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        # Status row
        status_row = ctk.CTkFrame(inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 6))
        self._nb_status_lbl = ctk.CTkLabel(status_row, text="TF-IDF+NB: checking…",
                                            text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11))
        self._nb_status_lbl.pack(side="left")
        self._db_status_lbl = ctk.CTkLabel(status_row, text="DistilBERT: checking…",
                                            text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=11))
        self._db_status_lbl.pack(side="left", padx=20)
        ctk.CTkButton(status_row, text="🔄 Refresh", command=self._refresh_model_status,
                       font=ctk.CTkFont(family="Inter", size=11), width=80, height=26,
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT_DARK, border_width=1, corner_radius=6).pack(side="right")

        # Controls
        ctrl = ctk.CTkFrame(inner, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(ctrl, text="Model:", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 4))
        self._model_var = ctk.StringVar(value="TF-IDF + Naive Bayes")
        ctk.CTkComboBox(ctrl, values=["TF-IDF + Naive Bayes", "DistilBERT", "Both Models"],
                         variable=self._model_var, width=180, state="readonly",
                         font=ctk.CTkFont(family="Inter", size=12),
                         fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                         button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                         dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                         dropdown_hover_color=SURFACE_HOVER,
                         ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(ctrl, text="Mode:", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 4))
        self._mode_var = ctk.StringVar(value="Fresh Training")
        ctk.CTkComboBox(ctrl, values=["Fresh Training", "Retrain (merge feedback)"],
                         variable=self._mode_var, width=200, state="readonly",
                         font=ctk.CTkFont(family="Inter", size=12),
                         fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                         button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                         dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                         dropdown_hover_color=SURFACE_HOVER,
                         ).pack(side="left", padx=(0, 12))

        self._train_btn = ctk.CTkButton(ctrl, text="▶ Start Training", command=self._on_start_training,
                                         font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                                         fg_color=ACCENT, hover_color=ACCENT_LIGHT, text_color="#1e1e2e",
                                         corner_radius=8, height=30)
        self._train_btn.pack(side="left", padx=(0, 8))

        self._abort_btn = ctk.CTkButton(ctrl, text="■ Abort", command=self._on_abort_training,
                                         font=ctk.CTkFont(family="Inter", size=12),
                                         fg_color="transparent", hover_color=SURFACE_HOVER,
                                         text_color=ERROR, border_color=ERROR, border_width=1,
                                         corner_radius=8, height=30)
        self._abort_btn_visible = False

        # Progress bar
        self._train_progress = ctk.CTkProgressBar(inner, fg_color=SURFACE, progress_color=ACCENT, height=8)
        self._train_progress.set(0)
        self._train_progress_visible = False

        # Log text box
        self._train_log = ctk.CTkTextbox(inner, height=120, state="disabled",
                                          fg_color=SURFACE, border_color=BORDER, border_width=1,
                                          text_color=TEXT_DIM, font=ctk.CTkFont(family="Monospace", size=10))
        self._train_log_visible = False

        # Threshold sliders
        thresh_frame = ctk.CTkFrame(inner, fg_color=SURFACE, corner_radius=8, border_color=BORDER, border_width=1)
        thresh_frame.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(thresh_frame, text="Classifier Thresholds",
                      font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                      text_color=TEXT).pack(anchor="w", padx=10, pady=(6, 4))

        self._rule_slider_var  = ctk.DoubleVar(value=6)
        self._ml_high_var      = ctk.DoubleVar(value=0.85)
        self._ml_low_var       = ctk.DoubleVar(value=0.65)

        def _slider_row(parent, label, variable, from_, to, fmt):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=label, width=200, anchor="w", text_color=TEXT_DIM,
                          font=ctk.CTkFont(family="Inter", size=11)).pack(side="left")
            sl = ctk.CTkSlider(row, variable=variable, from_=from_, to=to,
                                fg_color=SURFACE, progress_color=ACCENT, button_color=ACCENT)
            sl.pack(side="left", fill="x", expand=True, padx=(8, 8))
            lbl = ctk.CTkLabel(row, text=fmt(variable.get()), width=50, anchor="e", text_color=TEXT_DIM,
                                font=ctk.CTkFont(family="Inter", size=11))
            lbl.pack(side="left")
            variable.trace_add("write", lambda *_: lbl.configure(text=fmt(variable.get())))
            return sl

        _slider_row(thresh_frame, "Stage 1 Rule Score ≥", self._rule_slider_var, 1, 10,
                    lambda v: str(int(v)))
        _slider_row(thresh_frame, "Stage 2 ML High ≥",   self._ml_high_var, 0.5, 0.99,
                    lambda v: f"{v:.2f}")
        _slider_row(thresh_frame, "Stage 2 ML Low <",    self._ml_low_var, 0.4, 0.8,
                    lambda v: f"{v:.2f}")

        ctk.CTkButton(thresh_frame, text="💾 Save Thresholds", command=self._save_thresholds,
                       font=ctk.CTkFont(family="Inter", size=12),
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT_DARK, border_width=1, corner_radius=6, height=28,
                       ).pack(anchor="e", padx=10, pady=(4, 8))

    def _refresh_model_status(self) -> None:
        try:
            from classifier.config import MODEL_PATH, VECTORIZER_PATH, DISTILBERT_MODEL_DIR
            from datetime import datetime as _dt

            if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
                mtime    = max(MODEL_PATH.stat().st_mtime, VECTORIZER_PATH.stat().st_mtime)
                date_str = _dt.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                self._nb_status_lbl.configure(text=f"TF-IDF+NB: ✅ {date_str}", text_color=SUCCESS)
            else:
                self._nb_status_lbl.configure(text="TF-IDF+NB: ❌ Not trained", text_color=ERROR)

            db_config = DISTILBERT_MODEL_DIR / "config.json"
            if db_config.exists():
                mtime    = db_config.stat().st_mtime
                date_str = _dt.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                self._db_status_lbl.configure(text=f"DistilBERT: ✅ {date_str}", text_color=SUCCESS)
            else:
                self._db_status_lbl.configure(text="DistilBERT: ❌ Not trained", text_color=WARNING)
        except Exception as exc:
            logger.error("Could not refresh model status: %s", exc)

    def _load_thresholds(self) -> None:
        try:
            from classifier.config import load_thresholds
            t = load_thresholds()
            self._rule_slider_var.set(int(t.get("RULE_HIGH_THRESHOLD", 6)))
            self._ml_high_var.set(float(t.get("ML_HIGH_THRESHOLD", 0.85)))
            self._ml_low_var.set(float(t.get("ML_LOW_THRESHOLD", 0.65)))
        except Exception as exc:
            logger.warning("Could not load thresholds: %s", exc)

    def _save_thresholds(self) -> None:
        try:
            from classifier.config import save_thresholds
            rule_high = int(self._rule_slider_var.get())
            ml_high   = self._ml_high_var.get()
            ml_low    = self._ml_low_var.get()
            if ml_low >= ml_high:
                messagebox.showwarning("Invalid Thresholds",
                                        "ML Low threshold must be less than ML High threshold.")
                return
            save_thresholds(rule_high, ml_high, ml_low)
            messagebox.showinfo("Saved", "Thresholds saved. Restart the app to apply.")
        except Exception as exc:
            logger.error("Could not save thresholds: %s", exc)
            messagebox.showerror("Error", f"Failed to save thresholds:\n{exc}")

    def _on_start_training(self) -> None:
        if not self._data_dir:
            messagebox.showwarning("Not Ready", "Data directory is not set yet.")
            return

        model_map = {
            "TF-IDF + Naive Bayes": "nb_tfidf",
            "DistilBERT":           "distilbert",
            "Both Models":          "both",
        }
        model = model_map[self._model_var.get()]
        mode  = "retrain" if "Retrain" in self._mode_var.get() else "train"

        if model in ("distilbert", "both"):
            if not messagebox.askyesno("DistilBERT Training",
                                        "Fine-tuning DistilBERT can take 10–60 minutes on CPU.\nContinue?"):
                return

        from workers.training_worker import TrainingWorker
        candidate = self._data_dir
        project_dir = candidate
        for _ in range(4):
            if (candidate / "scripts" / "train_classifier.sh").exists():
                project_dir = candidate
                break
            candidate = candidate.parent

        self._training_worker = TrainingWorker(
            project_dir=project_dir, model=model, mode=mode,
            on_log_line=self._append_train_log,
            on_progress=lambda v: self._train_progress.set(v / 100),
            on_finished=self._on_training_done,
            ui_ref=self._scroll._parent_canvas if hasattr(self._scroll, "_parent_canvas") else None,
        )

        self._train_log.configure(state="normal")
        self._train_log.delete("0.0", "end")
        self._train_log.configure(state="disabled")
        if not self._train_log_visible:
            self._train_log.pack(fill="x", pady=(6, 0))
            self._train_log_visible = True
        if not self._train_progress_visible:
            self._train_progress.pack(fill="x", pady=(4, 0))
            self._train_progress_visible = True
        self._train_progress.set(0)
        self._train_btn.configure(state="disabled")
        if not self._abort_btn_visible:
            self._abort_btn.pack(side="left")
            self._abort_btn_visible = True

        self._training_worker.start()

    def _on_abort_training(self) -> None:
        if self._training_worker and self._training_worker.is_alive():
            self._training_worker.abort()

    def _append_train_log(self, line: str) -> None:
        self._train_log.configure(state="normal")
        self._train_log.insert("end", line + "\n")
        self._train_log.see("end")
        self._train_log.configure(state="disabled")

    def _on_training_done(self, success: bool, message: str) -> None:
        self._train_btn.configure(state="normal")
        if self._abort_btn_visible:
            self._abort_btn.pack_forget()
            self._abort_btn_visible = False
        if success:
            self._train_progress.set(1.0)
            self._append_train_log(f"✅ {message}")
            self._refresh_model_status()
        else:
            self._append_train_log(f"❌ {message}")
        if self.on_training_finished:
            self.on_training_finished(success, message)

    # ── Data management section ───────────────────────────────────────────────

    def _build_data_section(self, box: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))

        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(row1, text="Data folder:", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 8))
        self._data_dir_lbl = ctk.CTkLabel(row1, text="—", text_color=TEXT,
                                           font=ctk.CTkFont(family="Inter", size=12))
        self._data_dir_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row1, text="Change…", command=self._change_data_dir,
                       font=ctk.CTkFont(family="Inter", size=11), height=26,
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT_DARK, border_width=1, corner_radius=6).pack(side="right")

        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(row2, text="Clear cache for current month:", text_color=TEXT_DIM,
                      font=ctk.CTkFont(family="Inter", size=12)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row2, text="Clear Cache", command=lambda: self.on_clear_cache and self.on_clear_cache(""),
                       font=ctk.CTkFont(family="Inter", size=11), height=26,
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=WARNING,
                       border_color=WARNING, border_width=1, corner_radius=6).pack(side="left")

        ctk.CTkButton(inner, text="🔄 Re-authenticate Gmail",
                       command=lambda: self.on_reauth and self.on_reauth(),
                       font=ctk.CTkFont(family="Inter", size=12), height=30,
                       fg_color="transparent", hover_color=SURFACE_HOVER, text_color=ACCENT,
                       border_color=ACCENT_DARK, border_width=1, corner_radius=8).pack(anchor="w")

    def _change_data_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Choose Data Directory")
        if chosen and self.on_data_dir_changed:
            self.on_data_dir_changed(Path(chosen))

    # ── Load all ──────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        if self._data_dir:
            self._data_dir_lbl.configure(text=str(self._data_dir))
        self._load_budgets()
        self._load_ignore_list()
        self._load_rules()
        self._load_ai_backend()
        self._refresh_model_status()
        self._load_thresholds()

    def _save_config(self) -> None:
        if not self._data_dir:
            return
        try:
            (self._data_dir / "config.json").write_text(json.dumps(self._config, indent=2))
        except OSError as exc:
            logger.error("Could not save config.json: %s", exc)


# ── Helper dialogs ────────────────────────────────────────────────────────────

class _BudgetDialog(ctk.CTkToplevel):
    def __init__(self, parent, category: str) -> None:
        super().__init__(parent)
        self.title(f"Set Budget — {category}")
        self.geometry("320x160")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[float] = None
        self.configure(fg_color=BG)

        ctk.CTkLabel(self, text=f"Budget (₹) for {category}",
                      font=ctk.CTkFont(family="Inter", size=12), text_color=TEXT).pack(pady=(16, 4))
        self._entry = ctk.CTkEntry(self, placeholder_text="0",
                                    font=ctk.CTkFont(family="Inter", size=13),
                                    fg_color=SURFACE, border_color=BORDER, text_color=TEXT, width=180)
        self._entry.pack(pady=4)
        self._entry.focus()

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkButton(row, text="Save", command=self._on_save,
                       fg_color=ACCENT, text_color="#1e1e2e", corner_radius=8, width=90).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Cancel", command=self.destroy,
                       fg_color="transparent", text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                       corner_radius=8, width=90).pack(side="left")
        self.wait_window(self)

    def _on_save(self) -> None:
        try:
            self.result = float(self._entry.get() or "0")
        except ValueError:
            self.result = 0.0
        self.destroy()


class _AddRuleDialog(ctk.CTkToplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Add Custom Rule")
        self.geometry("380x230")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[dict] = None
        self.configure(fg_color=BG)

        def _row(label_text):
            f = ctk.CTkFrame(self, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(f, text=label_text, width=100, anchor="w",
                          text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=12)).pack(side="left")
            return f

        kw_row = _row("Keyword:");  self._kw = ctk.CTkEntry(kw_row, placeholder_text="e.g. grofers", width=200,
                                                              fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                                                              font=ctk.CTkFont(family="Inter", size=12)); self._kw.pack(side="left"); self._kw.focus()

        mi_row = _row("Matches in:")
        self._match_var = ctk.StringVar(value="both")
        ctk.CTkComboBox(mi_row, values=["both", "sender", "subject"], variable=self._match_var,
                         width=140, state="readonly",
                         fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                         button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                         dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                         dropdown_hover_color=SURFACE_HOVER,
                         font=ctk.CTkFont(family="Inter", size=12)).pack(side="left")

        cat_row = _row("Category:")
        self._cat_var = ctk.StringVar(value="Other")
        ctk.CTkComboBox(cat_row, values=ALL_CATEGORIES, variable=self._cat_var,
                         width=140, state="readonly",
                         fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                         button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                         dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                         dropdown_hover_color=SURFACE_HOVER,
                         font=ctk.CTkFont(family="Inter", size=12)).pack(side="left")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(btn_row, text="Save", command=self._on_save,
                       fg_color=ACCENT, text_color="#1e1e2e", corner_radius=8, width=90).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy,
                       fg_color="transparent", text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                       corner_radius=8, width=90).pack(side="left")
        self.wait_window(self)

    def _on_save(self) -> None:
        kw = self._kw.get().strip().lower()
        if kw:
            self.result = {"keyword": kw, "match_in": self._match_var.get(), "category": self._cat_var.get()}
        self.destroy()


# ── Separator helper ──────────────────────────────────────────────────────────

def _div(parent) -> None:
    ctk.CTkFrame(parent, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x", padx=0)
