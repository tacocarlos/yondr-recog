import tkinter as tk
import tkinter.ttk as ttk
from time import sleep

from reader.ocrreader import OCRReader

ocr_reader = OCRReader()


def on_detect(pouch_num: int):
    print(f"DETECTED POUCH: {pouch_num}")


ocr_reader.set_on_detect(on_detect)

app = tk.Tk()
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
camera_select.set(ocr_reader.list_cameras()[0].name)
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


def clear_cam(l: tk.Label):
    i = tk.PhotoImage(width=l.winfo_width(), height=l.winfo_height())
    l.photo_image = i
    l.config(image=l)


def stop_feed(w: tk.Label):
    id = ocr_reader.stop_capture()
    if id != "":
        w.after_cancel(id)
    clear_cam(w)


stop_camera = ttk.Button(buttons, text="Stop Camera", command=lambda: stop_feed(label))
stop_camera.pack()

app.mainloop()
