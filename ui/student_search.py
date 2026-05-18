"""Student fuzzy-search panel widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askokcancel
from typing import Callable

from rapidfuzz import fuzz, process

from student.student_record import Student, StudentRecord
from ui.dialogs import AddStudentDialog, ChangePouchDialog


class StudentSearchPanel(ttk.Frame):
    """
    A self-contained fuzzy search + selection panel backed by a StudentRecord.

    Layout (top → bottom):
    ┌──────────────────────────────┐
    │  Student Search              │  ← section header
    │  [  search entry  ]  [✕]     │  ← live search row
    │  12 of 30 students           │  ← result count
    │  ┌──────────────────────┐    │
    │  │ Alice Anderson  — #1 │    │  ← treeview (scrollable)
    │  │ Bob Baker       — #2 │    │
    │  └──────────────────────┘    │
    │  ─────────────────────────   │  ← separator
    │  Selected: Alice Anderson    │  ← selected-student footer
    │  [Turn In] [Change #] [+ New]│  ← action buttons
    └──────────────────────────────┘
    """

    _SCORE_THRESHOLD = 15  # rapidfuzz WRatio floor (0–100)
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
        self._tree.tag_configure("turned_in", foreground="#16A34A")

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=4, column=0, sticky="ew", padx=12, pady=(10, 6)
        )

        # Selected-student footer — badge label + info label sit side-by-side
        info_frame = ttk.Frame(self, style="Panel.TFrame")
        info_frame.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 8))

        self._badge_label = tk.Label(
            info_frame,
            text="",
            fg="#16A34A",  # green, matches the treeview turned_in tag
            bg="#FFFFFF",  # matches Panel.TFrame background
            font=("Helvetica", 13, "bold"),
        )
        self._badge_label.pack(side=tk.LEFT, padx=(0, 6))

        self._info_var = tk.StringVar(value="No student selected")
        ttk.Label(
            info_frame, textvariable=self._info_var, style="SelectedInfo.TLabel"
        ).pack(side=tk.LEFT)

        # Action buttons
        btn_frame = ttk.Frame(self, style="Panel.TFrame")
        btn_frame.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 14))

        self._turn_in_btn = ttk.Button(
            btn_frame,
            text="Turn In",
            style="Accent.TButton",
            state=tk.DISABLED,
            command=self._on_turn_in,
        )
        self._turn_in_btn.pack(side=tk.LEFT)

        self._change_pouch_btn = ttk.Button(
            btn_frame,
            text="Change Pouch #",
            state=tk.DISABLED,
            command=self._on_change_pouch,
        )
        self._change_pouch_btn.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            btn_frame,
            text="+ New Student",
            command=self._on_add_student,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            btn_frame,
            text="- Remove Student",
            command=self._on_remove_student,
        ).pack(side=tk.LEFT, padx=(8, 0))

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
                score_cutoff=self._SCORE_THRESHOLD,
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
        # Remember the selected IID so we can restore it after rebuilding
        prev = self._tree.selection()
        prev_iid = prev[0] if prev else None

        self._tree.delete(*self._tree.get_children())
        for s in self._results:
            badge = s.turned_in_badge()
            prefix = f"{badge}  " if badge else ""
            label = f"{prefix}{s.get_name()}   —   #{s.get_pouch()}"
            tags = ("turned_in",) if s.turned_in else ()
            self._tree.insert("", tk.END, iid=s.get_pouch(), text=label, tags=tags)

        # Re-select the previously selected row if it is still in the results.
        # This triggers <<TreeviewSelect>>, which keeps the badge, info label,
        # and Turn In / Check Out button in sync automatically.
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
        print(sel)
        if sel:
            pouch = sel[0]
            self._selected = self._record.students.get(pouch)
            if self._selected:
                self._info_var.set(
                    f"Selected:  {self._selected.get_name()}"
                    f"   —   Pouch #{self._selected.get_pouch()}"
                )
                self._badge_label.configure(text=self._selected.turned_in_badge())
            else:
                self._badge_label.configure(text="")
        else:
            self._selected = None
            self._info_var.set("No student selected")
            self._badge_label.configure(text="")

        # Enable/disable selection-dependent buttons and sync the toggle label
        btn_state = tk.NORMAL if self._selected else tk.DISABLED
        self._turn_in_btn.configure(state=btn_state)
        self._change_pouch_btn.configure(state=btn_state)
        self._update_turn_in_btn()

        # print(self._record.student_list)
        # print(self._record.students)
        if self._on_select_cb:
            self._on_select_cb(self._selected)

    def _update_turn_in_btn(self) -> None:
        """Switch the button between 'Turn In' and 'Check Out' to reflect the
        selected student's current turned_in status."""
        if self._selected and self._selected.turned_in:
            self._turn_in_btn.configure(text="Check Out", style="TButton")
        else:
            self._turn_in_btn.configure(text="Turn In", style="Accent.TButton")

    # ── Action handlers ───────────────────────────────────────────────────────

    def _on_turn_in(self) -> None:
        """Mark the selected student's pouch as turned in."""
        if not self._selected:
            return

        self._selected.toggle_turn_in()
        self._refresh(self._query_var.get())

    def _on_change_pouch(self) -> None:
        """Open the Change Pouch Number dialog for the selected student."""
        if not self._selected:
            return

        dlg = ChangePouchDialog(self, self._selected)

        if dlg.confirmed_pouch is not None:
            op = self._selected.get_pouch()
            self._record.change_pouch(self._selected.get_pouch(), dlg.confirmed_pouch)

            self._refresh(self._query_var.get())

    def _on_add_student(self) -> None:
        """Open the Add New Student dialog and insert the result into the record."""
        dlg = AddStudentDialog(self)

        if dlg.confirmed:
            self._record.add_student(
                dlg.first, dlg.middle, dlg.last, dlg.pouch, dlg.grade, turned_in=False
            )
            self._refresh(self._query_var.get())

    def _on_remove_student(self) -> None:
        if self._selected is None:
            return
        s = self._selected
        confirm = askokcancel("Remove Student?", f"Remove {s.get_name()} from list?")
        if not confirm:
            return

        self._record.remove_student(s)
        self._selected = None
        self._refresh(self._query_var.get())

    @property
    def selected(self) -> Student | None:
        """The currently selected Student, or None if nothing is selected."""
        return self._selected
