import tkinter as tk
from pathlib import Path
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror

from student.student_record import Student, StudentRecord
from ui.app import App


def get_ext(path: str):
    return Path(path).suffix


def create_test_student(first, last, p):
    s = Student()
    s.first = first
    s.middle = " "
    s.last = last
    s.pouch = p
    s.turned_in = False
    return s


sr = StudentRecord([])
src_file = askopenfilename(
    initialdir=Path(__file__).resolve(),
    filetypes=[("CSV File", "*.csv"), ("Database File", "*.sqlite")],
)


ext = get_ext(src_file)
if ext == ".csv":
    sr = StudentRecord.load_from_csv(src_file)
elif ext == ".sqlite":
    sr = StudentRecord.load_from_db(src_file)
else:
    d = showerror(
        "Failed to load",
        "Unable to load something that is not a csv or sqlite database",
    )
    exit()

print("Loaded student record.")


main_window = App(record=sr)
main_window.mainloop()
