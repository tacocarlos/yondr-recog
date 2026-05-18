"""Modal dialog boxes for student record operations."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, cast

from student.student_record import Student


class ChangePouchDialog(tk.Toplevel):
    """
    Ask the user for a new pouch number for an existing student.

    Usage (synchronous — blocks until the dialog closes):

        dlg = ChangePouchDialog(parent, student)
        if dlg.confirmed_pouch is not None:
            # TODO: apply dlg.confirmed_pouch to the student record
            pass
    """

    def __init__(self, parent: tk.Widget, student: Student) -> None:
        super().__init__(parent)
        self.title("Change Pouch Number")
        self.resizable(False, False)

        self._student = student
        self._confirmed_pouch: str | None = None

        self._build()

        # Centre over parent and make modal
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=(24, 20))
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        # Current student info (read-only)
        ttk.Label(frame, text="Student:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(
            frame,
            text=self._student.get_name(),
            font=("Helvetica", 11, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 4))

        ttk.Label(frame, text="Current pouch:").grid(
            row=1, column=0, sticky="w", pady=(0, 16)
        )
        ttk.Label(
            frame,
            text=f"#{self._student.get_pouch()}",
            font=("Helvetica", 11),
        ).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(0, 16))

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 16)
        )

        # New pouch number input
        ttk.Label(frame, text="New pouch #:").grid(row=3, column=0, sticky="w")
        self._new_pouch_var = tk.StringVar()
        entry = ttk.Entry(
            frame,
            textvariable=self._new_pouch_var,
            width=14,
            font=("Helvetica", 11),
        )
        entry.grid(row=3, column=1, sticky="w", padx=(12, 0))
        entry.focus_set()
        entry.bind("<Return>", lambda _: self._confirm())

        # Validation error label (hidden until needed)
        self._error_var = tk.StringVar()
        ttk.Label(
            frame,
            textvariable=self._error_var,
            foreground="#DC2626",
            font=("Helvetica", 10),
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # Buttons
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=5, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(
            btn_row, text="Confirm", style="Accent.TButton", command=self._confirm
        ).pack(side=tk.LEFT)

    # ── Validation & confirmation ─────────────────────────────────────────────

    def _confirm(self) -> None:
        raw = self._new_pouch_var.get().strip()
        if not raw:
            self._error_var.set("Pouch identifier cannot be empty.")
            return
        self._confirmed_pouch = raw
        self.destroy()

    # ── Result ────────────────────────────────────────────────────────────────

    @property
    def confirmed_pouch(self) -> str | None:
        """Validated new pouch string chosen by the user, or None if cancelled."""
        return self._confirmed_pouch


# ─────────────────────────────────────────────────────────────────────────────


class AddStudentDialog(tk.Toplevel):
    """
    Collect the details needed to create a new student record.

    Usage (synchronous — blocks until the dialog closes):

        dlg = AddStudentDialog(parent)
        if dlg.confirmed:
            # TODO: add the new student to the student record, e.g.:
            #   record.add_student(dlg.first, dlg.middle, dlg.last,
            #                      dlg.pouch, turned_in=False)
            pass
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("Add New Student")
        self.resizable(False, False)

        self._confirmed = False
        self._vars: dict[str, tk.StringVar] = {}

        self._build()

        # Centre over parent and make modal
        # cast as any to prevent basedpyright error
        self.transient(cast(Any, parent))
        self.grab_set()
        self.wait_window()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=(24, 20))
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        # Field definitions: (display label, internal key, required)
        fields: list[tuple[str, str, bool]] = [
            ("First name", "first", True),
            ("Middle name", "middle", False),
            ("Last name", "last", True),
            ("Pouch #", "pouch", True),
            ("Grade", "grade", True),
        ]

        entries: list[ttk.Entry] = []
        for i, (label, key, required) in enumerate(fields):
            marker = " *" if required else ""
            ttk.Label(frame, text=f"{label}{marker}").grid(
                row=i, column=0, sticky="w", pady=(0, 8)
            )
            var = tk.StringVar()
            self._vars[key] = var
            e = ttk.Entry(frame, textvariable=var, width=30, font=("Helvetica", 11))
            e.grid(row=i, column=1, sticky="ew", padx=(14, 0), pady=(0, 8))
            entries.append(e)

        # Pressing Enter in any field moves to the next, or confirms on the last
        for idx, e in enumerate(entries):
            next_entry = entries[idx + 1] if idx + 1 < len(entries) else None
            e.bind(
                "<Return>",
                (lambda ne: lambda _: ne.focus_set())(next_entry)
                if next_entry
                else lambda _: self._confirm(),
            )

        entries[0].focus_set()

        # Required-field note
        note_row = len(fields)
        ttk.Label(
            frame,
            text="* required",
            foreground="#6B7280",
            font=("Helvetica", 9),
        ).grid(row=note_row, column=0, columnspan=2, sticky="w", pady=(0, 4))

        # Validation error label
        self._error_var = tk.StringVar()
        ttk.Label(
            frame,
            textvariable=self._error_var,
            foreground="#DC2626",
            font=("Helvetica", 10),
        ).grid(row=note_row + 1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # Buttons
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=note_row + 2, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(
            btn_row,
            text="Add Student",
            style="Accent.TButton",
            command=self._confirm,
        ).pack(side=tk.LEFT)

    # ── Validation & confirmation ─────────────────────────────────────────────

    def _confirm(self) -> None:
        first = self._vars["first"].get().strip()
        last = self._vars["last"].get().strip()
        pouch_raw = self._vars["pouch"].get().strip()

        if not first:
            self._error_var.set("First name is required.")
            return
        if not last:
            self._error_var.set("Last name is required.")
            return
        if not pouch_raw:
            self._error_var.set("Pouch identifier is required.")
            return

        grade_raw = self._vars["grade"].get().strip()
        if not grade_raw.isdigit() or int(grade_raw) < 1:
            self._error_var.set("Grade must be a positive whole number.")
            return

        self._confirmed = True
        self.destroy()

    # ── Result properties ─────────────────────────────────────────────────────

    @property
    def confirmed(self) -> bool:
        """True if the user clicked Add Student and all fields were valid."""
        return self._confirmed

    @property
    def first(self) -> str:
        return self._vars["first"].get().strip()

    @property
    def middle(self) -> str:
        return self._vars["middle"].get().strip()

    @property
    def last(self) -> str:
        return self._vars["last"].get().strip()

    @property
    def pouch(self) -> str:
        """The validated pouch identifier. Only call this when confirmed is True."""
        return self._vars["pouch"].get().strip()

    @property
    def grade(self) -> int:
        """The validated grade. Only call this when confirmed is True."""
        return int(self._vars["grade"].get().strip())
