import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from tkinter import filedialog, messagebox

from reader.ocrreader import OCRReader
from student.student_record import StudentRecord
from ui.photoimg import ImageLabel


def get_ext(path: str):
    return Path(path).suffix


app = tk.Tk()

ocr_reader = OCRReader()
sr = StudentRecord([])
src_file = filedialog.askopenfilename(
    initialdir=Path(__file__).resolve(),
    filetypes=[("CSV File", "*.csv"), ("Database File", "*.sqlite")],
    # parent=app,
)

ext = get_ext(src_file)
if ext == ".csv":
    sr = StudentRecord.load_from_csv(src_file)
elif ext == ".sqlite":
    sr = StudentRecord.load_from_db(src_file)
else:
    d = messagebox.showerror(
        "Failed to load",
        "Unable to load something that is not a csv or sqlite database",
    )
    exit()

print("Loaded student record.")


def on_detect(pouch_num: int):
    print(f"DETECTED POUCH: {pouch_num}")


ocr_reader.set_on_detect(on_detect)

app.bind("<Escape>", lambda e: app.quit())

camera = ttk.Frame(app, width=1200, height=900)
camera.pack(side=tk.LEFT)

buttons = ttk.Frame(app)
buttons.pack(side=tk.BOTTOM)

turn_in_frame = ttk.Frame(app)
turn_in_frame.pack(side=tk.RIGHT)

cam_choice = tk.StringVar()
camera_select = ttk.Combobox(camera, textvariable=cam_choice)
camera_select["values"] = list(c.name for c in ocr_reader.list_cameras())
camera_select.set(ocr_reader.list_cameras()[0].index)
camera_select.pack()


def select_cam(event):
    name = event.widget.get()
    cam = ocr_reader.get_camera(name)
    if cam is not None:
        ocr_reader.select_camera(cam)


camera_select.bind("<<ComboboxSelected>>", select_cam)
label = tk.Label(camera, image=tk.PhotoImage(), width=1200, height=900)
label.pack()


def start_feed(w):
    print("started camera")
    ocr_reader.start_capture(w)


start_camera = ttk.Button(buttons, text="Start Camera")
start_camera.config(command=lambda: start_feed(label))
start_camera.pack()


def clear_cam(label: ImageLabel):
    i = tk.PhotoImage(width=l.winfo_width(), height=l.winfo_height())
    label.photo_image = i
    label.config(image=i)


def stop_feed(w: tk.Label):
    id = ocr_reader.stop_capture()
    if id != "":
        w.after_cancel(id)
    clear_cam(w)


stop_camera = ttk.Button(buttons, text="Stop Camera", command=lambda: stop_feed(label))
stop_camera.pack()

app.mainloop()
