"""Main application window."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showinfo

from reader.ocrreader import OCRReader
from student.student_record import Student, StudentRecord
from ui.pouch_search import PouchSearchPanel
from ui.student_search import StudentSearchPanel

# Shown in the camera label before a feed starts
_CAM_PLACEHOLDER_TEXT = "No camera feed"
_CAM_PLACEHOLDER_W = 90  # chars — sets initial column width
_CAM_PLACEHOLDER_H = 400  # px  — reserves vertical space


class App(tk.Tk):
    """
    Root window layout:

    ┌──────────────────────────────┬───┬─────────────────────────┐
    │                              │   │  Student Search          │
    │       Camera feed            │ │ │  [search entry] [✕]     │
    │       (OCRReader widget)     │ │ │  ─────────────────────── │
    │                              │ │ │  Alice Anderson — #1     │
    │                              │ │ │  Bob Baker      — #2     │
    │                              │ │ │  ...                     │
    │                              │   │  ─────────────────────── │
    │                              │   │  Selected: Alice A.      │
    ├──────────────────────────────┤   └─────────────────────────┘
    │ [Camera ▾]  [▶ Start] [■ Stop]                              │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, record: StudentRecord) -> None:
        super().__init__()
        self.title("Yondr Recognition")
        self.resizable(True, True)

        self._reader = OCRReader()
        self._record = record

        def on_detect(pouch: str):
            s = self._record.students.get(pouch)
            if s is None:
                return
            s.turn_in()
            showinfo("Pouch Turned in", f"Turned In: {str(s)}")

        self._reader.set_on_detect(on_detect)

        self._setup_styles()
        self._build()
        self._size_search_panel()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Styles ────────────────────────────────────────────────────────────────

    def _setup_styles(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")

        BG = "#F3F4F6"  # window background
        PANEL = "#FFFFFF"  # right panel background
        ACCENT = "#2563EB"  # start button / selection highlight
        ACCENT_HOV = "#1D4ED8"
        DANGER = "#DC2626"  # stop button
        DANGER_HOV = "#B91C1C"
        MUTED = "#6B7280"  # secondary text
        BORDER = "#E5E7EB"  # subtle borders
        TEXT = "#111827"  # primary text
        CAM_BG = "#1F2937"  # dark placeholder behind the camera

        self.configure(bg=BG)

        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Cam.TFrame", background=CAM_BG)
        s.configure("TSeparator", background=BORDER)

        # Labels
        s.configure("TLabel", background=BG, foreground=TEXT, font=("Helvetica", 11))
        s.configure(
            "PanelHeader.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("Helvetica", 15, "bold"),
        )
        s.configure(
            "Muted.TLabel", background=PANEL, foreground=MUTED, font=("Helvetica", 10)
        )
        s.configure(
            "SelectedInfo.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("Helvetica", 11),
        )
        s.configure(
            "CamPlaceholder.TLabel",
            background=CAM_BG,
            foreground=MUTED,
            font=("Helvetica", 13),
        )

        # Entry
        s.configure(
            "Search.TEntry",
            fieldbackground=BG,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )

        # Buttons
        s.configure("TButton", font=("Helvetica", 11), padding=(10, 6))

        s.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="white",
            font=("Helvetica", 11, "bold"),
            padding=(14, 7),
        )
        s.map(
            "Accent.TButton",
            background=[("disabled", "#93C5FD"), ("active", ACCENT_HOV)],
        )

        s.configure(
            "Stop.TButton",
            background=DANGER,
            foreground="white",
            font=("Helvetica", 11, "bold"),
            padding=(14, 7),
        )
        s.map(
            "Stop.TButton", background=[("disabled", "#FCA5A5"), ("active", DANGER_HOV)]
        )

        s.configure("Clear.TButton", padding=(4, 5), font=("Helvetica", 11))

        # Treeview
        s.configure(
            "Student.Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=30,
            font=("Helvetica", 11),
            bordercolor=BORDER,
            relief="flat",
        )
        s.map(
            "Student.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "white")],
        )
        s.configure("Student.Treeview.Heading", font=("Helvetica", 11, "bold"))

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        self._outer = outer

        # Three columns: [camera] [divider] [search panel]
        outer.columnconfigure(0, weight=0)  # camera — fixed width
        outer.columnconfigure(1, weight=0)  # divider
        outer.columnconfigure(2, weight=1)  # search — expands
        outer.rowconfigure(0, weight=1)  # content row stretches
        outer.rowconfigure(1, weight=0)  # controls row is fixed

        # ── Camera feed ───────────────────────────────────────────────────────
        cam_frame = ttk.Frame(outer, style="Cam.TFrame")
        cam_frame.grid(row=0, column=0, sticky="nsew")
        cam_frame.rowconfigure(0, weight=1)
        cam_frame.columnconfigure(0, weight=1)

        self._cam_label = ttk.Label(
            cam_frame,
            text=_CAM_PLACEHOLDER_TEXT,
            style="CamPlaceholder.TLabel",
            anchor="center",
            width=_CAM_PLACEHOLDER_W,
        )
        self._cam_label.grid(
            row=0, column=0, sticky="nsew", ipadx=0, ipady=_CAM_PLACEHOLDER_H // 2
        )

        # ── Vertical divider ──────────────────────────────────────────────────
        ttk.Separator(outer, orient=tk.VERTICAL).grid(
            row=0, column=1, sticky="ns", padx=14
        )

        # ── Right column: name search (top) + pouch search (bottom) ──────────
        right_col = ttk.Frame(outer)
        right_col.grid(row=0, column=2, sticky="nsew")
        right_col.columnconfigure(0, weight=1)
        right_col.rowconfigure(0, weight=2)  # name search — gets more vertical space
        right_col.rowconfigure(1, weight=0)  # horizontal divider
        right_col.rowconfigure(2, weight=1)  # pouch search

        # Name search
        name_panel = ttk.Frame(right_col, style="Panel.TFrame")
        name_panel.grid(row=0, column=0, sticky="nsew")
        name_panel.rowconfigure(0, weight=1)
        name_panel.columnconfigure(0, weight=1)

        self._search = StudentSearchPanel(
            name_panel,
            self._record,
            on_select=self._on_student_selected,
            style="Panel.TFrame",
        )
        self._search.grid(row=0, column=0, sticky="nsew")

        ttk.Separator(right_col, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky="ew"
        )

        # Pouch search
        pouch_panel = ttk.Frame(right_col, style="Panel.TFrame")
        pouch_panel.grid(row=2, column=0, sticky="nsew")
        pouch_panel.rowconfigure(0, weight=1)
        pouch_panel.columnconfigure(0, weight=1)

        self._pouch_search = PouchSearchPanel(
            pouch_panel,
            self._record,
            on_select=self._on_pouch_selected,
            style="Panel.TFrame",
        )
        self._pouch_search.grid(row=0, column=0, sticky="nsew")

        # ── Camera controls (span full width, below camera) ───────────────────
        ctrl = ttk.Frame(outer)
        ctrl.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 0))

        # Camera selector drop-down
        cameras = OCRReader.list_cameras()
        self._cam_infos = cameras
        cam_names = [c.name for c in cameras] or ["No cameras found"]

        self._cam_var = tk.StringVar(value=cam_names[0])
        cam_combo = ttk.Combobox(
            ctrl,
            textvariable=self._cam_var,
            values=cam_names,
            state="readonly",
            width=30,
            font=("Helvetica", 11),
        )
        cam_combo.pack(side=tk.LEFT, padx=(0, 10))

        self._start_btn = ttk.Button(
            ctrl,
            text="▶  Start",
            style="Accent.TButton",
            command=self._start_camera,
            state=tk.NORMAL if cameras else tk.DISABLED,
        )
        self._start_btn.pack(side=tk.LEFT)

        self._stop_btn = ttk.Button(
            ctrl,
            text="■  Stop",
            style="Stop.TButton",
            command=self._stop_camera,
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        def export_command():
            fp = asksaveasfilename()
            if fp == "":
                return
            self._record.export_csv(fp)

        self._export_btn = ttk.Button(
            ctrl, text="Export as CSV", command=export_command, state=tk.NORMAL
        )

        self._export_btn.pack(side=tk.LEFT)

    # ── Sizing ─────────────────────────────────────────────────────────────────

    def _size_search_panel(self) -> None:
        """
        Set the search panel column's minsize so the widest possible
        'Selected: …' footer string is never clipped at startup.
        """
        info_font = tkfont.Font(family="Helvetica", size=11)
        badge_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        inner_pad = 14 * 2  # padx=14 on each side of the info frame
        badge_gap = 6  # padx=(0, 6) between badge label and info label

        # Worst-case badge width: the checkmark that appears when turned in
        badge_px = badge_font.measure("\u2713") + badge_gap

        if self._record.student_list:
            # Measure both footer formats and take the wider one
            name_search_widths = (
                info_font.measure(
                    f"Selected:  {s.get_name()}   —   Pouch #{s.get_pouch()}"
                )
                for s in self._record.student_list
            )
            pouch_search_widths = (
                info_font.measure(
                    f"{s.get_name()}   —   Pouch #{s.get_pouch()}   —   Grade {s.grade}"
                )
                for s in self._record.student_list
            )
            max_text_px = max(max(name_search_widths), max(pouch_search_widths))
        else:
            max_text_px = info_font.measure("No student selected")

        self._outer.columnconfigure(2, minsize=badge_px + max_text_px + inner_pad)

    # ── Camera control ────────────────────────────────────────────────────────

    def _start_camera(self) -> None:
        name = self._cam_var.get()
        cam = self._reader.get_camera(name)
        if cam is None:
            return
        self._reader.select_camera(cam)
        self._reader.start_capture(self._cam_label)
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)

    def _stop_camera(self) -> None:
        after_id = self._reader.stop_capture()
        if after_id:
            self._cam_label.after_cancel(after_id)
        self._start_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_student_selected(self, student: Student | None) -> None:
        """Called whenever the user picks (or deselects) a student."""
        pass  # hook for callers — extend as needed

    def _on_pouch_selected(self, student: Student | None) -> None:
        """Called whenever the user picks (or deselects) a student via the pouch search."""
        pass  # hook for callers — extend as needed

    def _on_close(self) -> None:
        self._stop_camera()
        self.destroy()
