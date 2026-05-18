"""Pouch-ID lookup panel widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from student.student_record import Student, StudentRecord


class PouchSearchPanel(ttk.Frame):
    """
    Look up a student by typing their Yondr pouch identifier.

    Matches are ranked by specificity: exact → starts-with → contains
    (all comparisons are case-insensitive).

    Layout (top → bottom):
    ┌──────────────────────────────┐
    │  Search by Pouch             │  ← header
    │  [  pouch query  ]  [✕]    │  ← live search row
    │  3 of 30 students            │  ← result count
    │  ┌──────────┬─────────────┐ │
    │  │ Pouch    │ Student      │ │  ← two-column treeview
    │  │ #A1      │ Alice A.     │ │
    │  └──────────┴─────────────┘ │
    │  ──────────────────────────  │  ← separator
    │  ✓ Alice Anderson — Gr. 5   │  ← selected-student footer
    └──────────────────────────────┘
    """

    def __init__(
        self,
        parent: tk.Widget,
        record: StudentRecord,
        on_select: Callable[[Student | None], None] | None = None,
        **kw,
    ) -> None:
        super().__init__(parent, **kw)
        self._record = record
        self._results: list[Student] = []
        self._selected: Student | None = None
        self._on_select_cb = on_select
        self._build()
        self._refresh("")

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        # Header
        ttk.Label(self, text="Search by Pouch", style="PanelHeader.TLabel").grid(
            row=0, column=0, sticky="ew", padx=12, pady=(12, 6)
        )

        # Search entry + clear button
        entry_row = ttk.Frame(self, style="Panel.TFrame")
        entry_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        entry_row.columnconfigure(0, weight=1)

        self._query_var = tk.StringVar()
        self._query_var.trace_add(
            "write", lambda *_: self._refresh(self._query_var.get())
        )

        entry = ttk.Entry(
            entry_row,
            textvariable=self._query_var,
            style="Search.TEntry",
            font=("Helvetica", 12),
        )
        entry.grid(row=0, column=0, sticky="ew", ipady=4)

        ttk.Button(
            entry_row,
            text="✕",
            width=3,
            style="Clear.TButton",
            command=lambda: self._query_var.set(""),
        ).grid(row=0, column=1, padx=(6, 0))

        # Result count
        self._count_var = tk.StringVar()
        ttk.Label(self, textvariable=self._count_var, style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", padx=14, pady=(0, 4)
        )

        # Two-column treeview + scrollbar
        tree_frame = ttk.Frame(self, style="Panel.TFrame")
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=12)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self._tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=scroll.set,
            selectmode="browse",
            columns=("pouch", "name"),
            show="headings",
            style="Student.Treeview",
        )
        self._tree.heading("pouch", text="Pouch")
        self._tree.heading("name", text="Student")
        self._tree.column("pouch", width=90, minwidth=60, stretch=False, anchor="w")
        self._tree.column("name", stretch=True, anchor="w")

        scroll.configure(command=self._tree.yview)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.tag_configure("turned_in", foreground="#16A34A")

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=4, column=0, sticky="ew", padx=12, pady=(10, 6)
        )

        # Selected-student footer — badge + info side-by-side
        info_frame = ttk.Frame(self, style="Panel.TFrame")
        info_frame.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 12))

        self._badge_label = tk.Label(
            info_frame,
            text="",
            fg="#16A34A",
            bg="#FFFFFF",
            font=("Helvetica", 13, "bold"),
        )
        self._badge_label.pack(side=tk.LEFT, padx=(0, 6))

        self._info_var = tk.StringVar(value="No pouch selected")
        ttk.Label(
            info_frame, textvariable=self._info_var, style="SelectedInfo.TLabel"
        ).pack(side=tk.LEFT)

    # ── Search logic ──────────────────────────────────────────────────────────

    def _refresh(self, query: str) -> None:
        """Filter students by pouch ID, ranked exact → starts-with → contains."""
        q = query.strip().lower()
        students = self._record.student_list

        if not q:
            self._results = list(students)
        else:
            exact = [s for s in students if s.get_pouch().lower() == q]
            starts = [
                s
                for s in students
                if s.get_pouch().lower().startswith(q) and s.get_pouch().lower() != q
            ]
            contains = [
                s
                for s in students
                if q in s.get_pouch().lower()
                and not s.get_pouch().lower().startswith(q)
            ]
            self._results = exact + starts + contains

        self._repopulate_tree()

    def _repopulate_tree(self) -> None:
        prev = self._tree.selection()
        prev_iid = prev[0] if prev else None

        self._tree.delete(*self._tree.get_children())
        for s in self._results:
            badge = s.turned_in_badge()
            name_cell = f"{badge}  {s.get_name()}" if badge else s.get_name()
            tags = ("turned_in",) if s.turned_in else ()
            self._tree.insert(
                "",
                tk.END,
                iid=s.get_pouch(),
                values=(s.get_pouch(), name_cell),
                tags=tags,
            )

        if prev_iid and self._tree.exists(prev_iid):
            self._tree.selection_set(prev_iid)
            self._tree.see(prev_iid)

        n = len(self._results)
        total = len(self._record.student_list)
        self._count_var.set(
            f"{n} of {total} students" if n < total else f"{total} students"
        )

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_tree_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if sel:
            pouch = sel[0]  # IID is the pouch string directly
            self._selected = self._record.students.get(pouch)
            if self._selected:
                self._info_var.set(
                    f"{self._selected.get_name()}"
                    f"   —   Pouch #{self._selected.get_pouch()}"
                    f"   —   Grade {self._selected.grade}"
                )
                self._badge_label.configure(text=self._selected.turned_in_badge())
            else:
                self._badge_label.configure(text="")
        else:
            self._selected = None
            self._info_var.set("No pouch selected")
            self._badge_label.configure(text="")

        if self._on_select_cb:
            self._on_select_cb(self._selected)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def selected(self) -> Student | None:
        """The currently selected Student, or None if nothing is selected."""
        return self._selected
