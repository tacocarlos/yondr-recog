import tkinter as tk
from typing import Any


class ImageLabel(tk.Label):
    photo_image: tk.PhotoImage

    # TODO: figure out which class 'master' should be
    def __init__(self, photo_img: tk.PhotoImage, master: Any = None, cnf={}, **kwargs):
        tk.Label.__init__(master, cnf, kwargs)
        self.photo_image = photo_img

    def set_image(self, p: tk.PhotoImage):
        self.photo_image = p
        self.config(image=p)
