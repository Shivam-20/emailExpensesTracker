"""
main_window.py — CTk MainWindow: sidebar + 5-tab main area.
Supports single-month, date-range, full-year, and all-available multi-fetch.
"""

import calendar
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from tabs.expenses_tab      import ExpensesTab
from tabs.charts_tab        import ChartsTab
from tabs.trends_tab        import TrendsTab
from tabs.review_queue_tab  import ReviewQueueTab
from tabs.settings_tab      import SettingsTab
from workers.gmail_worker   import GmailWorker, AuthOnlyWorker
from core.db                import Database
from core.gmail_auth        import is_authenticated, CREDENTIALS_PATH, revoke_credentials
from styles import (
    ACCENT, ACCENT_DARK, ACCENT_LIGHT,
    BG, BORDER, BORDER_BRIGHT, SIDEBAR_BG, SURFACE, SURFACE_HOVER,
    TEXT, TEXT_DIM, TEXT_MUTE,
    SUCCESS, SUCCESS_BG, WARNING, ERROR,
    FONT_SIZE_SM, FONT_SIZE_XS, FONT_SIZE_XL,
    SPACING_SM, SPACING_MD,
)

logger = logging.getLogger(__name__)

_NOW_YEAR  = datetime.now().year
_NOW_MONTH = datetime.now().month

_YEARS = [str(y) for y in range(_NOW_YEAR - 4, _NOW_YEAR + 2)]
_MONTHS_LONG  = list(calendar.month_name[1:])
_MONTHS_SHORT = list(calendar.month_abbr[1:])


def _month_idx_to_num(idx: int) -> int:
    return idx + 1


def _num_to_month_idx(month: int) -> int:
    return month - 1


class MainWindow:
    """Main application window composed of sidebar + tab area."""

    def __init__(self, root: ctk.CTk, data_dir: Path) -> None:
        self._root      = root
        self.data_dir   = data_dir
        self._worker: Optional[GmailWorker] = None
        self._auth_worker: Optional[AuthOnlyWorker] = None
        self._labels: list[dict] = []
        self._current_rows: list[dict] = []
        self._config    = self._load_config(data_dir)
        self._db        = Database(data_dir)
        self._db.connect()

        # Multi-fetch state
        self._fetch_queue: list[tuple[int, int]] = []
        self._fetch_accumulated: list[dict] = []
        self._fetch_total: int = 0
        self._fetch_stats: dict[str, int | bool] = self._empty_fetch_stats()
        self._fetch_force: bool = False
        self._fetch_label_id: Optional[str] = None

        self._root.title("💰 Gmail Expense Tracker")
        self._root.geometry("1200x760")
        self._root.minsize(1100, 720)
        self._root.configure(fg_color=BG)

        self._setup_ui()
        self._post_init()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Config ────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_config(data_dir: Path) -> dict:
        cfg_file = data_dir / "config.json"
        try:
            if cfg_file.exists():
                return json.loads(cfg_file.read_text())
        except Exception as exc:
            logger.debug("Could not load config.json: %s", exc)
        return {}

    @staticmethod
    def _empty_fetch_stats() -> dict[str, int | bool]:
        return {
            "candidate_count": 0,
            "processed_count": 0,
            "parsed_count": 0,
            "no_amount_count": 0,
            "ignored_count": 0,
            "parse_failures": 0,
            "new_rows": 0,
            "truncated": False,
        }

    def _merge_fetch_stats(self, stats: Optional[dict]) -> None:
        if not stats:
            return
        for key in (
            "candidate_count", "processed_count", "parsed_count",
            "no_amount_count", "ignored_count", "parse_failures", "new_rows",
        ):
            self._fetch_stats[key] = int(self._fetch_stats[key]) + int(stats.get(key, 0))
        self._fetch_stats["truncated"] = bool(self._fetch_stats["truncated"] or stats.get("truncated"))

    def _build_fetch_status_message(self, row_count: int) -> str:
        issues: list[str] = []
        parse_failures = int(self._fetch_stats["parse_failures"])
        if parse_failures:
            issues.append(f"{parse_failures} parse failure(s)")
        if self._fetch_stats["truncated"]:
            issues.append("Gmail search capped at 500 candidates")

        prefix = "⚠" if issues else "✅"
        message = f"{prefix} Loaded {row_count} expense(s)"
        if issues:
            message += " • " + " • ".join(issues)
        return message

    def _build_fetch_warning_lines(self) -> list[str]:
        warnings: list[str] = []
        parse_failures = int(self._fetch_stats["parse_failures"])
        candidate_count = int(self._fetch_stats["candidate_count"])
        ignored_count = int(self._fetch_stats["ignored_count"])
        no_amount_count = int(self._fetch_stats["no_amount_count"])

        if self._fetch_stats["truncated"]:
            warnings.append(
                "Gmail search hit the 500 candidate cap. Narrow the label/date range if results look incomplete."
            )
        if parse_failures:
            warnings.append(f"{parse_failures} email(s) failed during parsing and were skipped.")
        if no_amount_count:
            warnings.append(f"{no_amount_count} candidate email(s) were ignored because no amount was detected.")
        if ignored_count:
            warnings.append(f"{ignored_count} candidate email(s) were skipped by the ignore list.")
        if candidate_count and not warnings:
            warnings.append(f"Processed {candidate_count} Gmail candidate email(s) without fetch warnings.")
        return warnings

    def _resolve_chart_period(self) -> tuple[int, int, Optional[float]]:
        chart_year, chart_month = datetime.now().year, datetime.now().month
        prev_total: Optional[float] = None

        if self._fetch_total == 1 and self._fetch_mode_var.get() == "Single Month":
            chart_year = int(self._year_combo.get())
            chart_month = _MONTHS_LONG.index(self._month_combo.get()) + 1
            prev_total = self._compute_prev_month_total(chart_year, chart_month)

        return chart_year, chart_month, prev_total

    def _refresh_derived_views(self, preserve_expense_filters: bool = True) -> None:
        chart_year, chart_month, prev_total = self._resolve_chart_period()
        self._expenses_tab.set_db(self._db)
        self._expenses_tab.refresh_rows(self._current_rows, preserve_filters=preserve_expense_filters)
        self._charts_tab.update_charts(self._current_rows, chart_year, chart_month, prev_total)
        self._settings_tab.refresh()
        self._review_tab.refresh()
        self._trends_tab.refresh()
        self._update_review_badge()
        self._update_summary_card(self._current_rows, prev_total)

    def _apply_review_correction_to_current_rows(
        self,
        msg_id: str,
        new_status: str,
        new_category: Optional[str] = None,
    ) -> bool:
        for row in self._current_rows:
            if row.get("id") != msg_id:
                continue
            row["status"] = new_status
            row["needs_review"] = 0
            if new_category:
                row["category_edited"] = new_category
            return True
        return False

    # ── UI Construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self._root.grid_columnconfigure(0, weight=0)
        self._root.grid_columnconfigure(1, weight=1)
        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_rowconfigure(1, weight=0)

        self._build_sidebar()
        self._build_main_area()
        self._build_status_bar()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        # Outer frame (fixed width, full height)
        sidebar = ctk.CTkFrame(
            self._root, width=272, fg_color=SIDEBAR_BG,
            corner_radius=0, border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Scrollable inner content
        inner = ctk.CTkScrollableFrame(
            sidebar, fg_color=SIDEBAR_BG,
            scrollbar_button_color=BORDER_BRIGHT,
            scrollbar_button_hover_color=ACCENT_DARK,
            corner_radius=0,
        )
        inner.pack(fill="both", expand=True, padx=0, pady=0)

        def _section_label(parent: ctk.CTkFrame, text: str) -> None:
            ctk.CTkLabel(
                parent, text=text,
                font=ctk.CTkFont(family="Inter", size=FONT_SIZE_XS, weight="bold"),
                text_color=TEXT_DIM,
                anchor="w",
            ).pack(fill="x", padx=(14, 0), pady=(8, 2))

        def _sep(parent: ctk.CTkFrame) -> None:
            ctk.CTkFrame(parent, height=1, fg_color=BORDER, corner_radius=0).pack(
                fill="x", padx=10, pady=6,
            )

        # Title
        ctk.CTkLabel(
            inner, text="💰 Expense Tracker",
            font=ctk.CTkFont(family="Inter", size=FONT_SIZE_XL, weight="bold"),
            text_color=ACCENT,
        ).pack(pady=(16, 4))

        # Account pill
        self._account_pill = ctk.CTkLabel(
            inner, text="Not connected",
            font=ctk.CTkFont(family="Inter", size=FONT_SIZE_SM),
            text_color=TEXT_DIM,
            fg_color=SURFACE,
            corner_radius=999,
        )
        self._account_pill.pack(fill="x", padx=14, pady=(0, 4), ipady=4)

        self._connect_btn = ctk.CTkButton(
            inner, text="🔑 Connect Gmail",
            command=self._on_connect,
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            text_color=ACCENT,
            border_color=ACCENT_DARK,
            border_width=1,
            corner_radius=8,
            height=28,
        )
        self._connect_btn.pack(fill="x", padx=14, pady=(0, 6))

        _sep(inner)
        _section_label(inner, "FETCH MODE")

        self._fetch_mode_var = ctk.StringVar(value="Single Month")
        self._fetch_mode = ctk.CTkComboBox(
            inner,
            values=["Single Month", "Month Range", "Full Year", "All Available"],
            variable=self._fetch_mode_var,
            command=self._on_fetch_mode_changed,
            state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE,
            border_color=BORDER_BRIGHT,
            text_color=TEXT,
            button_color=SURFACE_HOVER,
            button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            dropdown_hover_color=SURFACE_HOVER,
        )
        self._fetch_mode.pack(fill="x", padx=14, pady=(4, 4))

        # ── Single month pickers ───────────────────────────────────────────
        self._single_row = ctk.CTkFrame(inner, fg_color="transparent")
        yr_var = ctk.StringVar(value=str(_NOW_YEAR))
        mo_var = ctk.StringVar(value=_MONTHS_LONG[_NOW_MONTH - 1])
        self._year_combo  = ctk.CTkComboBox(
            self._single_row, values=_YEARS, variable=yr_var, width=80, state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
            button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE, dropdown_text_color=TEXT, dropdown_hover_color=SURFACE_HOVER,
        )
        self._month_combo = ctk.CTkComboBox(
            self._single_row, values=_MONTHS_LONG, variable=mo_var, width=110, state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
            button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE, dropdown_text_color=TEXT, dropdown_hover_color=SURFACE_HOVER,
        )
        self._year_combo.pack(side="left", padx=(0, 4))
        self._month_combo.pack(side="left")
        self._single_row.pack(fill="x", padx=14, pady=2)

        # ── Range pickers ──────────────────────────────────────────────────
        self._range_row = ctk.CTkFrame(inner, fg_color="transparent")

        def _range_pair(parent, label_text, default_year_str, default_month_idx):
            ctk.CTkLabel(parent, text=label_text, text_color=TEXT_DIM, width=30,
                         font=ctk.CTkFont(family="Inter", size=11)).pack(side="left")
            yr = ctk.CTkComboBox(parent, values=_YEARS, width=72, state="readonly",
                                  font=ctk.CTkFont(family="Inter", size=12),
                                  fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
                                  button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                                  dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                                  dropdown_hover_color=SURFACE_HOVER)
            yr.set(default_year_str)
            yr.pack(side="left", padx=(2, 2))
            mo = ctk.CTkComboBox(parent, values=_MONTHS_SHORT, width=72, state="readonly",
                                  font=ctk.CTkFont(family="Inter", size=12),
                                  fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
                                  button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
                                  dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
                                  dropdown_hover_color=SURFACE_HOVER)
            mo.set(_MONTHS_SHORT[default_month_idx])
            mo.pack(side="left")
            return yr, mo

        from_frame = ctk.CTkFrame(self._range_row, fg_color="transparent")
        from_frame.pack(fill="x", pady=1)
        self._from_year, self._from_month = _range_pair(
            from_frame, "From", str(_NOW_YEAR - 1), 0)

        to_frame = ctk.CTkFrame(self._range_row, fg_color="transparent")
        to_frame.pack(fill="x", pady=1)
        self._to_year, self._to_month = _range_pair(
            to_frame, "To  ", str(_NOW_YEAR), _NOW_MONTH - 1)

        self._range_row.pack(fill="x", padx=14, pady=2)
        self._range_row.pack_forget()

        # ── Full year picker ───────────────────────────────────────────────
        self._year_only_row = ctk.CTkFrame(inner, fg_color="transparent")
        self._year_only_combo = ctk.CTkComboBox(
            self._year_only_row, values=_YEARS, state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
            button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE, dropdown_text_color=TEXT, dropdown_hover_color=SURFACE_HOVER,
        )
        self._year_only_combo.set(str(_NOW_YEAR))
        self._year_only_combo.pack(fill="x")
        self._year_only_row.pack(fill="x", padx=14, pady=2)
        self._year_only_row.pack_forget()

        # ── Gmail label filter ─────────────────────────────────────────────
        self._label_var = ctk.StringVar(value="📂 All Mail")
        self._label_combo = ctk.CTkComboBox(
            inner, values=["📂 All Mail"], variable=self._label_var, state="readonly",
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color=SURFACE, border_color=BORDER_BRIGHT, text_color=TEXT,
            button_color=SURFACE_HOVER, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE, dropdown_text_color=TEXT, dropdown_hover_color=SURFACE_HOVER,
        )
        self._label_combo.pack(fill="x", padx=14, pady=(4, 2))

        # Last fetched
        self._last_fetched_lbl = ctk.CTkLabel(
            inner, text="Last fetched: —",
            text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=FONT_SIZE_SM),
        )
        self._last_fetched_lbl.pack(pady=(2, 0))

        _sep(inner)
        _section_label(inner, "ACTIONS")

        self._fetch_btn = ctk.CTkButton(
            inner, text="🔍 Fetch Expenses",
            command=lambda: self._on_fetch(force=False),
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_LIGHT, text_color="#1e1e2e",
            corner_radius=8, height=34,
        )
        self._fetch_btn.pack(fill="x", padx=14, pady=(4, 4))

        self._refresh_btn = ctk.CTkButton(
            inner, text="🔄 Force Refresh",
            command=lambda: self._on_fetch(force=True),
            font=ctk.CTkFont(family="Inter", size=12),
            fg_color="transparent", hover_color=SURFACE_HOVER,
            text_color=ACCENT, border_color=ACCENT_DARK, border_width=1,
            corner_radius=8, height=28,
        )
        self._refresh_btn.pack(fill="x", padx=14, pady=(0, 6))

        _sep(inner)
        _section_label(inner, "SUMMARY")

        self._summary_frame = _SummaryCard(inner)
        self._summary_frame.pack(fill="x", padx=14, pady=(4, 6))

        # Stage 3 label
        self._stage3_lbl = ctk.CTkLabel(
            inner, text="",
            text_color=TEXT_DIM,
            font=ctk.CTkFont(family="Inter", size=FONT_SIZE_SM),
        )
        self._stage3_lbl.pack(pady=(4, 0))

        ctk.CTkLabel(
            inner, text="Alt+1–5 tabs  •  keyboard friendly",
            text_color=TEXT_MUTE,
            font=ctk.CTkFont(family="Inter", size=FONT_SIZE_XS),
        ).pack(pady=(2, 16))

    # ── Main area / tabs ──────────────────────────────────────────────────────

    def _build_main_area(self) -> None:
        self._tabs = ctk.CTkTabview(
            self._root,
            fg_color=BG,
            segmented_button_fg_color=SURFACE,
            segmented_button_selected_color=BG,
            segmented_button_selected_hover_color=SURFACE_HOVER,
            segmented_button_unselected_color=SURFACE,
            segmented_button_unselected_hover_color=SURFACE_HOVER,
            text_color=TEXT,
            text_color_disabled=TEXT_DIM,
            border_color=BORDER,
            border_width=1,
        )
        self._tabs.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=(0, 0))

        for tab_name in ["📋 Expenses", "📊 Charts", "📈 Trends", "🔍 Review Queue", "⚙️ Settings"]:
            self._tabs.add(tab_name)

        # Build tabs
        self._expenses_tab   = ExpensesTab(self._tabs.tab("📋 Expenses"),   db=self._db)
        self._charts_tab     = ChartsTab(self._tabs.tab("📊 Charts"))
        self._trends_tab     = TrendsTab(self._tabs.tab("📈 Trends"))
        self._review_tab     = ReviewQueueTab(self._tabs.tab("🔍 Review Queue"))
        self._settings_tab   = SettingsTab(self._tabs.tab("⚙️ Settings"))

        # Wire up callbacks
        self._expenses_tab.on_field_changed   = self._on_field_changed
        self._expenses_tab.on_exclude         = self._on_exclude_requested
        self._expenses_tab.on_review          = self._on_review_requested
        self._review_tab.on_corrected  = self._on_review_correction
        self._settings_tab.on_reauth          = self._on_reauth
        self._settings_tab.on_clear_cache     = self._on_clear_cache
        self._settings_tab.on_data_dir_changed = self._on_data_dir_changed
        self._settings_tab.on_backend_changed = self._on_backend_changed
        self._settings_tab.on_training_finished = self._on_training_finished
        self._charts_tab.on_category_drill    = self._on_chart_category_drill

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(self._root, height=28, fg_color=SIDEBAR_BG,
                            corner_radius=0, border_width=0)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            bar, text="Ready",
            text_color=TEXT_DIM, font=ctk.CTkFont(family="Inter", size=FONT_SIZE_SM),
            anchor="w",
        )
        self._status_lbl.pack(side="left", padx=10)

        self._cancel_btn = ctk.CTkButton(
            bar, text="✕ Cancel",
            command=self._on_cancel_fetch,
            font=ctk.CTkFont(family="Inter", size=11),
            fg_color="transparent", hover_color=SURFACE_HOVER,
            text_color=TEXT_DIM, border_color=BORDER_BRIGHT, border_width=1,
            corner_radius=6, height=22, width=80,
        )
        # hidden by default — placed with pack_forget
        self._cancel_btn_visible = False

        self._progress = ctk.CTkProgressBar(
            bar,
            width=200, height=8,
            fg_color=SURFACE, progress_color=ACCENT,
            corner_radius=4,
        )
        self._progress.set(0)
        # hidden by default
        self._progress_visible = False

    def _show_status(self, msg: str) -> None:
        self._status_lbl.configure(text=msg)

    def _show_progress(self, show: bool) -> None:
        if show and not self._progress_visible:
            self._cancel_btn.pack(side="right", padx=(0, 4), pady=3)
            self._progress.pack(side="right", padx=(0, 8), pady=3)
            self._progress_visible = True
        elif not show and self._progress_visible:
            self._cancel_btn.pack_forget()
            self._progress.pack_forget()
            self._progress_visible = False

    # ── Post init ─────────────────────────────────────────────────────────────

    def _post_init(self) -> None:
        self._settings_tab.set_db(self._db, self.data_dir, self._config)
        self._trends_tab.set_db(self._db, self.data_dir)
        self._review_tab.set_db(self._db, self.data_dir)
        self._update_stage3_label()
        self._update_review_badge()
        self._setup_shortcuts()
        if not CREDENTIALS_PATH.exists():
            self._account_pill.configure(text="⚠ credentials.json missing")
            return
        if is_authenticated(self.data_dir):
            self._auth_worker = AuthOnlyWorker(
                data_dir=self.data_dir,
                on_authenticated=self._on_authenticated,
                on_labels_ready=self._on_labels_ready,
                on_error=lambda msg: logger.warning("Auth-only: %s", msg),
                ui_ref=self._root,
            )
            self._auth_worker.start()

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        tab_names = ["📋 Expenses", "📊 Charts", "📈 Trends", "🔍 Review Queue", "⚙️ Settings"]
        for i, name in enumerate(tab_names, start=1):
            self._root.bind(f"<Alt-Key-{i}>", lambda e, n=name: self._tabs.set(n))
        self._root.bind("<Alt-f>", lambda e: (
            self._on_fetch(force=False) if self._fetch_btn.cget("state") != "disabled" else None
        ))

    # ── Fetch mode UI toggling ───────────────────────────────────────────────

    def _on_fetch_mode_changed(self, _val: str = "") -> None:
        mode = self._fetch_mode_var.get()
        if mode == "Single Month":
            self._single_row.pack(fill="x", padx=14, pady=2)
            self._range_row.pack_forget()
            self._year_only_row.pack_forget()
        elif mode == "Month Range":
            self._single_row.pack_forget()
            self._range_row.pack(fill="x", padx=14, pady=2)
            self._year_only_row.pack_forget()
        elif mode == "Full Year":
            self._single_row.pack_forget()
            self._range_row.pack_forget()
            self._year_only_row.pack(fill="x", padx=14, pady=2)
        else:
            self._single_row.pack_forget()
            self._range_row.pack_forget()
            self._year_only_row.pack_forget()

        labels = {
            "Single Month":  "🔍 Fetch Expenses",
            "Month Range":   "🔍 Fetch Date Range",
            "Full Year":     "🔍 Fetch Full Year",
            "All Available": "🔍 Load All Cached",
        }
        self._fetch_btn.configure(text=labels.get(mode, "🔍 Fetch Expenses"))

    # ── Fetch orchestration ───────────────────────────────────────────────────

    def _build_fetch_months(self) -> list[tuple[int, int]]:
        mode = self._fetch_mode_var.get()
        if mode == "Single Month":
            year  = int(self._year_combo.get())
            month = _MONTHS_LONG.index(self._month_combo.get()) + 1
            return [(year, month)]

        elif mode == "Full Year":
            year = int(self._year_only_combo.get())
            return [(year, m) for m in range(1, 13)]

        elif mode == "Month Range":
            fy = int(self._from_year.get())
            fm = _MONTHS_SHORT.index(self._from_month.get()) + 1
            ty = int(self._to_year.get())
            tm = _MONTHS_SHORT.index(self._to_month.get()) + 1
            if (fy, fm) > (ty, tm):
                fy, fm, ty, tm = ty, tm, fy, fm
            months: list[tuple[int, int]] = []
            y, m = fy, fm
            while (y, m) <= (ty, tm):
                months.append((y, m))
                m += 1
                if m > 12:
                    m = 1; y += 1
                if len(months) > 60:
                    break
            return months

        else:  # All Available
            try:
                available = self._db.get_available_months()
                return [(int(s[:4]), int(s[5:7])) for s in available] if available else \
                       [(_NOW_YEAR, _NOW_MONTH)]
            except Exception as exc:
                logger.debug("Could not load available months: %s", exc)
                return [(_NOW_YEAR, _NOW_MONTH)]

    def _on_fetch(self, force: bool = False) -> None:
        if not CREDENTIALS_PATH.exists():
            self._msgbox_warning("Missing credentials.json",
                                  "Place credentials.json in the app directory.")
            return
        if self._worker and self._worker.is_alive():
            self._worker.abort()
            self._worker.join(2)

        months = self._build_fetch_months()
        if not months:
            return

        self._fetch_queue       = list(months)
        self._fetch_accumulated = []
        self._fetch_total       = len(months)
        self._fetch_stats       = self._empty_fetch_stats()
        self._fetch_force       = force
        # Map current label selection
        curr_label = self._label_var.get()
        self._fetch_label_id = next(
            (lbl["id"] for lbl in self._labels if lbl["name"] == curr_label.strip("📂 ")),
            None
        )

        self._fetch_btn.configure(state="disabled")
        self._refresh_btn.configure(state="disabled")
        self._show_progress(True)
        self._progress.set(0)
        self._expenses_tab.clear()
        self._charts_tab.clear()

        self._start_next_fetch()

    def _start_next_fetch(self) -> None:
        if not self._fetch_queue:
            self._on_all_fetches_complete()
            return

        year, month = self._fetch_queue.pop(0)
        done = self._fetch_total - len(self._fetch_queue) - 1
        suffix = f" ({done + 1}/{self._fetch_total})" if self._fetch_total > 1 else ""
        self._show_status(f"Fetching {calendar.month_name[month]} {year}…{suffix}")

        rules = self._settings_tab.get_custom_rules()
        self._worker = GmailWorker(
            data_dir=self.data_dir, year=year, month=month,
            label_id=self._fetch_label_id, force_refresh=self._fetch_force,
            custom_rules=rules,
            on_progress=self._on_month_progress,
            on_status=self._show_status,
            on_authenticated=self._on_authenticated,
            on_labels_ready=self._on_labels_ready,
            on_finished=self._on_month_fetch_finished,
            on_error=self._on_worker_error,
            ui_ref=self._root,
        )
        self._worker.start()

    def _on_month_progress(self, current: int, total: int) -> None:
        done = self._fetch_total - len(self._fetch_queue) - 1
        base_pct = done / self._fetch_total
        month_pct = (current / total / self._fetch_total) if total > 0 else (1 / self._fetch_total)
        self._progress.set(min(base_pct + month_pct, 1.0))

    def _on_month_fetch_finished(self, rows: list) -> None:
        self._merge_fetch_stats(getattr(self._worker, "stats", None))
        self._fetch_accumulated.extend(rows)
        done = self._fetch_total - len(self._fetch_queue)
        self._progress.set(done / self._fetch_total)
        self._start_next_fetch()

    def _on_all_fetches_complete(self) -> None:
        rows = self._fetch_accumulated
        self._current_rows = rows

        self._refresh_derived_views(preserve_expense_filters=False)

        self._fetch_btn.configure(state="normal")
        self._refresh_btn.configure(state="normal")
        self._show_progress(False)
        self._last_fetched_lbl.configure(
            text=f"Last fetched: {datetime.now().strftime('%H:%M')}",
            text_color=WARNING if self._fetch_stats["truncated"] or int(self._fetch_stats["parse_failures"]) else SUCCESS,
        )
        self._show_status(self._build_fetch_status_message(len(rows)) if rows else "No expenses found.")

        warning_lines = self._build_fetch_warning_lines()
        if warning_lines and (self._fetch_stats["truncated"] or int(self._fetch_stats["parse_failures"])):
            self._msgbox_warning("Fetch Completed With Warnings", "\n".join(warning_lines))

        if not rows:
            n = self._fetch_total
            label = "the selected period" if n > 1 else \
                    f"{_MONTHS_LONG[_MONTHS_LONG.index(self._month_combo.get())]} {self._year_combo.get()}"
            self._msgbox_info("No Expenses Found",
                               f"No expense emails found for {label}.")

    def _on_cancel_fetch(self) -> None:
        if self._worker and self._worker.is_alive():
            self._worker.abort()
        self._fetch_queue = []
        self._fetch_btn.configure(state="normal")
        self._refresh_btn.configure(state="normal")
        self._show_progress(False)
        self._show_status("Fetch cancelled.")

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
        except Exception as exc:
            logger.debug("Could not compute prev month total: %s", exc)
            return None

    def _on_connect(self) -> None:
        if not CREDENTIALS_PATH.exists():
            self._msgbox_warning("Missing credentials.json",
                                  f"Place credentials.json in:\n{CREDENTIALS_PATH}")
            return
        self._account_pill.configure(text="Connecting…", text_color=TEXT_DIM)
        self._auth_worker = AuthOnlyWorker(
            data_dir=self.data_dir,
            on_authenticated=self._on_authenticated,
            on_labels_ready=self._on_labels_ready,
            on_error=self._on_worker_error,
            ui_ref=self._root,
        )
        self._auth_worker.start()

    def _on_authenticated(self, email: str) -> None:
        self._account_pill.configure(
            text=f"● {email}", text_color=SUCCESS, fg_color=SUCCESS_BG,
        )
        self._connect_btn.pack_forget()
        self._show_status(f"Connected as {email}")

    def _on_labels_ready(self, labels: list) -> None:
        self._labels = labels
        names = ["📂 All Mail"] + [lbl["name"] for lbl in labels]
        self._label_combo.configure(values=names)
        self._label_var.set("📂 All Mail")

    # ── Summary card ──────────────────────────────────────────────────────────

    def _update_summary_card(self, rows: list, prev_total: Optional[float] = None) -> None:
        active = [r for r in rows if r.get("status") != "excluded"]
        if not active:
            self._summary_frame.update("—", "—", "—", "")
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

        self._summary_frame.update(f"₹{total:,.0f}", f"{len(active)} txns", top_cat[:14], delta_str)

    # ── Field change ──────────────────────────────────────────────────────────

    def _on_field_changed(self, msg_id: str, field: str, value) -> None:
        try:
            self._db.update_expense_field(msg_id, field, value)
        except Exception as exc:
            logger.error("Persist failed %s/%s: %s", msg_id, field, exc)

        if field == "status" and value == "review":
            try:
                self._db.conn.execute(
                    "UPDATE expenses SET needs_review = 1 WHERE id = ?", (msg_id,)
                )
                self._db.conn.commit()
            except Exception as exc:
                logger.error("Could not set needs_review: %s", exc)

        for r in self._current_rows:
            if r.get("id") == msg_id:
                r[field] = value
                break

        if field in ("amount_edited", "category_edited", "status"):
            y = int(self._year_combo.get()) if self._fetch_mode_var.get() == "Single Month" \
                else _NOW_YEAR
            m = (_MONTHS_LONG.index(self._month_combo.get()) + 1) \
                if self._fetch_mode_var.get() == "Single Month" else _NOW_MONTH
            self._charts_tab.update_charts(self._current_rows, y, m)
            self._update_summary_card(self._current_rows)
            self._trends_tab.refresh()

        if field == "status":
            self._review_tab.refresh()
            self._update_review_badge()

    # ── Worker error ──────────────────────────────────────────────────────────

    def _on_worker_error(self, msg: str) -> None:
        self._fetch_btn.configure(state="normal")
        self._refresh_btn.configure(state="normal")
        self._show_progress(False)
        self._show_status("❌ Error")
        self._msgbox_error("Error", msg)

    # ── Tab signal equivalents ────────────────────────────────────────────────

    def _on_exclude_requested(self, msg_id: str, sender_email: str) -> None:
        if self._msgbox_yesno("Add to Ignore List?",
                               f"Also ignore future emails from {sender_email}?"):
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

    def _on_review_correction(
        self,
        msg_id: str,
        new_label: str,
        new_category: Optional[str] = None,
    ) -> None:
        self._apply_review_correction_to_current_rows(msg_id, new_label, new_category)
        self._refresh_derived_views(preserve_expense_filters=True)
        if new_label == "active":
            self._show_status("✅ Review correction saved and expense restored.")
        else:
            self._show_status("✅ Review correction saved and item excluded.")

    def _on_training_finished(self, success: bool, message: str) -> None:
        if success:
            self._show_status("✅ Model training completed.")
        else:
            self._show_status(f"❌ Training failed: {message}")

    def _on_chart_category_drill(self, category: str) -> None:
        self._tabs.set("📋 Expenses")
        self._expenses_tab.filter_by_category(category)

    # ── Review badge ──────────────────────────────────────────────────────────

    def _update_review_badge(self) -> None:
        count = self._review_tab.get_review_count()
        badge = f"🔍 Review Queue" + (f" ({count})" if count > 0 else "")
        self._tabs.tab("🔍 Review Queue")  # tab always exists; text is the key in CTkTabview

    # ── Settings callbacks ────────────────────────────────────────────────────

    def _on_reauth(self) -> None:
        revoke_credentials(self.data_dir)
        self._account_pill.configure(text="Not connected", text_color=TEXT_DIM, fg_color=SURFACE)
        self._connect_btn.pack(fill="x", padx=14, pady=(0, 6))
        self._msgbox_info("Re-authenticate",
                           "Cleared. Click Connect Gmail to log in again.")

    def _on_clear_cache(self, month_str: str) -> None:
        if not month_str:
            if self._fetch_mode_var.get() == "Single Month":
                year  = int(self._year_combo.get())
                month = _MONTHS_LONG.index(self._month_combo.get()) + 1
                month_str = f"{year}-{month:02d}"
            else:
                month_str = f"{_NOW_YEAR}-{_NOW_MONTH:02d}"
        if self._msgbox_yesno("Clear Cache", f"Delete cached expenses for {month_str}?"):
            self._db.delete_month(month_str)
            self._expenses_tab.clear()
            self._charts_tab.clear()
            self._show_status(f"Cache cleared for {month_str}.")

    def _on_data_dir_changed(self, new_path: Path) -> None:
        self._msgbox_info("Restart Required",
                           f"Data directory will change to:\n{new_path}\n\nRestart the app to apply.")
        _BOOTSTRAP_FILE.write_text(str(new_path))

    def _on_backend_changed(self, backend: str) -> None:
        self._update_stage3_label()

    def _update_stage3_label(self) -> None:
        try:
            from classifier.config import _load_stage3_backend
            backend = _load_stage3_backend()
        except Exception as exc:
            logger.debug("Could not load stage3 backend: %s", exc)
            backend = "distilbert"
        if backend == "phi4-mini":
            import urllib.request
            try:
                urllib.request.urlopen("http://localhost:11434", timeout=2)
                self._stage3_lbl.configure(text="🦙 Stage 3: phi4-mini ✅", text_color=SUCCESS)
            except Exception:
                self._stage3_lbl.configure(text="🦙 Stage 3: phi4-mini ⚠️", text_color=WARNING)
        else:
            self._stage3_lbl.configure(text="🧠 Stage 3: DistilBERT", text_color=TEXT_DIM)

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _msgbox_info(self, title: str, msg: str) -> None:
        import tkinter.messagebox as mb
        mb.showinfo(title, msg)

    def _msgbox_warning(self, title: str, msg: str) -> None:
        import tkinter.messagebox as mb
        mb.showwarning(title, msg)

    def _msgbox_error(self, title: str, msg: str) -> None:
        import tkinter.messagebox as mb
        mb.showerror(title, msg)

    def _msgbox_yesno(self, title: str, msg: str) -> bool:
        import tkinter.messagebox as mb
        return mb.askyesno(title, msg)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        if self._worker and self._worker.is_alive():
            self._worker.abort()
            self._worker.join(3)
        self._db.close()
        self._root.destroy()


# ── Summary card widget ───────────────────────────────────────────────────────

class _SummaryCard(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=SURFACE, corner_radius=8, border_color=BORDER, border_width=1)

        self._total_lbl = ctk.CTkLabel(
            self, text="—",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=TEXT,
        )
        self._total_lbl.pack(pady=(8, 2))

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="x", padx=8, pady=(0, 2))
        self._count_lbl = ctk.CTkLabel(
            mid, text="—", anchor="w",
            font=ctk.CTkFont(family="Inter", size=11), text_color=TEXT_DIM,
        )
        self._count_lbl.pack(side="left", fill="x", expand=True)
        self._cat_lbl = ctk.CTkLabel(
            mid, text="—", anchor="e",
            font=ctk.CTkFont(family="Inter", size=11), text_color=TEXT_DIM,
        )
        self._cat_lbl.pack(side="right", fill="x", expand=True)

        self._delta_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family="Inter", size=10), text_color=TEXT_DIM,
        )
        self._delta_lbl.pack(pady=(0, 8))

    def update(self, total: str, count: str, top_cat: str, delta: str) -> None:
        self._total_lbl.configure(text=total)
        self._count_lbl.configure(text=count)
        self._cat_lbl.configure(text=top_cat)
        self._delta_lbl.configure(text=delta)
