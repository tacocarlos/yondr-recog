"""Student fuzzy-search panel widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from rapidfuzz import fuzz, process

from student.student_record import Student, StudentRecord


class StudentSearchPanel(ttk.Frame):
    """
    A self-contained fuzzy search + selection panel backed by a StudentRecord.

    Layout (top → bottom):
    ┌──────────────────────────────┐
    │  Student Search              │  ← section header
    │  [  search entry  ]  [✕]   │  ← live search row
    │  12 of 30 students           │  ← result count
    │  ┌──────────────────────┐   │
    │  │ Alice Anderson  — #1 │   │  ← treeview (scrollable)
    │  │ Bob Baker       — #2 │   │
    │  └──────────────────────┘   │
    │  ─────────────────────────   │  ← separator
    │  Selected: Alice Anderson    │  ← selected-student footer
    └──────────────────────────────┘
    """

    _SCORE_THRESHOLD = 35  # rapidfuzz WRatio floor (0–100)
    _MAX_RESULTS = 60

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
        self._refresh("")  # populate the list immediately

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        # Header label
        ttk.Label(self, text="Student Search", style="PanelHeader.TLabel").grid(
            row=0, column=0, sticky="ew", padx=12, pady=(12, 6)
        )

        # Search entry + clear button
        search_row = ttk.Frame(self, style="Panel.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        search_row.columnconfigure(0, weight=1)

        self._query_var = tk.StringVar()
        self._query_var.trace_add(
            "write", lambda *_: self._refresh(self._query_var.get())
        )

        entry = ttk.Entry(
            search_row,
            textvariable=self._query_var,
            style="Search.TEntry",
            font=("Helvetica", 12),
        )
        entry.grid(row=0, column=0, sticky="ew", ipady=4)
        entry.focus_set()

        ttk.Button(
            search_row,
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

        # Treeview + scrollbar
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
            show="tree",
            style="Student.Treeview",
        )
        scroll.configure(command=self._tree.yview)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=4, column=0, sticky="ew", padx=12, pady=(10, 6)
        )

        # Selected-student footer
        self._info_var = tk.StringVar(value="No student selected")
        ttk.Label(self, textvariable=self._info_var, style="SelectedInfo.TLabel").grid(
            row=5, column=0, sticky="w", padx=14, pady=(0, 12)
        )

    # ── Search logic ──────────────────────────────────────────────────────────

    def _refresh(self, query: str) -> None:
        """Re-run the fuzzy search and repopulate the treeview."""
        students = self._record.student_list

        if query.strip():
            names = [s.get_name() for s in students]
            matches = process.extract(
                query,
                names,
                scorer=fuzz.WRatio,
                limit=self._MAX_RESULTS,
            )
            # Build a name→student map; preserve score-ranked order
            name_to_student = {s.get_name(): s for s in students}
            self._results = [
                name_to_student[name]
                for name, score, _ in matches
                if score >= self._SCORE_THRESHOLD and name in name_to_student
            ]
        else:
            self._results = list(students)

        self._repopulate_tree()

    def _repopulate_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for s in self._results:
            label = f"{s.get_name()}   —   #{s.get_pouch()}"
            self._tree.insert("", tk.END, iid=str(s.get_pouch()), text=label)

        n = len(self._results)
        total = len(self._record.student_list)
        self._count_var.set(
            f"{n} of {total} students" if n < total else f"{total} students"
        )

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_tree_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if sel:
            pouch = int(sel[0])
            self._selected = self._record.students.get(pouch)
            if self._selected:
                self._info_var.set(
                    f"Selected:  {self._selected.get_name()}"
                    f"   —   Pouch #{self._selected.get_pouch()}"
                )
        else:
            self._selected = None
            self._info_var.set("No student selected")

        if self._on_select_cb:
            self._on_select_cb(self._selected)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def selected(self) -> Student | None:
        """The currently selected Student, or None if nothing is selected."""
        return self._selected
