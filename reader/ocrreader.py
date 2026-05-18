from tkinter import Widget
from tkinter.ttk import Label
from typing import Callable, cast

import cv2 as cv
import easyocr
import numpy as np
from cv2_enumerate_cameras import enumerate_cameras
from cv2_enumerate_cameras.camera_info import CameraInfo
from PIL import Image, ImageTk
from ultralytics import YOLO


class OCRReader:
    POUCH_HEIGHT = 300
    DETECT_COUNT = 3

    def __init__(self):
        self.camera_enabled = False
        self.reader = easyocr.Reader(["en"])
        self.model = YOLO("yolo26n-seg.pt")
        self.cam: cv.VideoCapture | None = None
        self.on_detect_callbacks: list[Callable[[str], None]] = []
        self.detection_buffer = []
        self.after_id = ""

    def set_on_detect(self, cb: Callable[[str], None]):
        self.on_detect_callbacks.append(cb)

    def clear_detect_callbacks(self):
        self.on_detect_callbacks = []

    def __trigger_detect(self, pouch: str):
        for cb in self.on_detect_callbacks:
            cb(pouch)

    def camera_ready(self) -> bool:
        return self.cam is not None and self.cam.isOpened()

    @staticmethod
    def list_cameras() -> list[CameraInfo]:
        return list(enumerate_cameras())

    def select_camera(self, cam: CameraInfo) -> cv.VideoCapture:
        self.cam = cv.VideoCapture(cam.index, cam.backend)
        return self.cam

    def get_camera(self, name: str) -> CameraInfo | None:
        c = None
        for cam in self.list_cameras():
            if cam.name == name:
                c = cam
                break
        return c

    def __apply_frame(self, label: Label, frame: cv.typing.MatLike):
        frame = cv.resize(frame, (1200, 800))
        img = Image.fromarray(cv.cvtColor(frame, cv.COLOR_BGR2RGBA))
        photo_img = ImageTk.PhotoImage(image=img)
        label.photo_image = photo_img
        label.configure(image=photo_img)

    def update_frame(self, widget: Label):
        if self.camera_ready() is False:
            return
        cam = cast(cv.VideoCapture, self.cam)
        ret, frame = cam.read()
        results = self.model(frame, verbose=False)
        crops = [
            frame[y1:y2, x1:x2].copy()
            for result in results
            for box in result.boxes
            if result.names[int(box.cls[0])] in ("cell phone", "laptop", "remote")
            for x1, y1, x2, y2 in [map(int, box.xyxy[0])]
        ]
        if len(crops) > 0:
            crops = [crops[0]]
        pouch = self.___pack_pouch(crops)
        frame = self.__draw_boxes(frame, results)
        self.__apply_frame(widget, frame)

        if pouch is not None:
            img_rgb = cv.cvtColor(pouch, cv.COLOR_BGR2RGB)
            result = self.reader.readtext(img_rgb)
            for bb, txt, _ in result:
                print(txt)
                txt = txt.strip()
                if txt:
                    self.detection_buffer.append(txt)

                    if len(self.detection_buffer) >= OCRReader.DETECT_COUNT:
                        if len(set(self.detection_buffer)) > 1:
                            self.detection_buffer = []
                        else:
                            pouch = self.__draw_text_box(pouch, "POUCH DETECTED")
                            self.__trigger_detect(self.detection_buffer[0])
                else:
                    self.detection_buffer = []
                self.__apply_frame(widget, pouch)
        else:
            self.detection_buffer = []

        if self.camera_enabled:
            self.after_id = widget.after(10, lambda: self.update_frame(widget))
        else:
            self.after_id = ""

    def start_capture(self, widget: Label):
        self.camera_enabled = True
        self.update_frame(widget)

    def stop_capture(self):
        self.camera_enabled = False
        return self.after_id

    @staticmethod
    def __label_color(class_id: int) -> tuple[int, int, int]:
        """Map a class ID to a unique-ish BGR color via HSV hue spreading."""
        hue = int((class_id * 37) % 180)  # prime step spreads hues evenly
        hsv = np.array([[[hue, 220, 255]]], dtype=np.uint8)
        bgr = cv.cvtColor(hsv, cv.COLOR_HSV2BGR)[0][0]
        return (int(bgr[0]), int(bgr[1]), int(bgr[2]))

    @staticmethod
    def ___pack_pouch(
        crops: list[np.ndarray], height: int = POUCH_HEIGHT
    ) -> np.ndarray | None:
        """
        Resize every crop to a common height (preserving aspect ratio) and
        concatenate them side-by-side into a single displayable image.
        Returns None when the crop list is empty.
        """
        if not crops:
            return None

        strips = []
        for crop in crops:
            h, w = crop.shape[:2]
            if h == 0 or w == 0:
                continue
            scale = height / h
            resized = cv.resize(crop, (max(1, int(w * scale)), height))
            strips.append(resized)

        return np.hstack(strips) if strips else None

    @staticmethod
    def __draw_boxes(frame: np.ndarray, results) -> np.ndarray:
        """Draw bounding boxes and labels for every detection onto frame."""
        for result in results:
            boxes = result.boxes
            names = result.names
            for box in boxes:
                cls_id = int(box.cls[0])
                label = names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                color = OCRReader.__label_color(cls_id)

                # Bounding box
                cv.rectangle(frame, (x1, y1), (x2, y2), color, thickness=2)

                # Label background + text
                text = f"{label} {conf:.2f}"
                (tw, th), baseline = cv.getTextSize(
                    text, cv.FONT_HERSHEY_SIMPLEX, fontScale=2, thickness=1
                )
                tag_y = max(y1 - 4, th + baseline)
                cv.rectangle(
                    frame,
                    (x1, tag_y - th - baseline),
                    (x1 + tw + 4, tag_y + baseline),
                    color,
                    thickness=cv.FILLED,
                )
                # Choose black or white text for legibility against the tag
                # color is BGR, so index 0=B, 1=G, 2=R
                brightness = color[0] * 0.114 + color[1] * 0.587 + color[2] * 0.299
                text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                cv.putText(
                    frame,
                    text,
                    (x1 + 2, tag_y),
                    cv.FONT_HERSHEY_SIMPLEX,
                    fontScale=2,
                    color=text_color,
                    thickness=1,
                    lineType=cv.LINE_AA,
                )

        return frame

    @staticmethod
    def __draw_text_box(
        frame: np.ndarray,
        text: str,
        font=cv.FONT_HERSHEY_SIMPLEX,
        font_scale: float = 0.8,
        thickness: int = 2,
        padding: int = 20,
        line_gap: int = 8,
        bg_color: tuple[int, int, int] = (60, 60, 60),
        bg_alpha: float = 0.65,
        text_color: tuple[int, int, int] = (255, 255, 255),
    ) -> np.ndarray:
        """
        Render a semi-transparent text box centered on the frame.
        Supports multi-line text via newlines in `text`.
        """
        frame_h, frame_w = frame.shape[:2]
        lines = text.splitlines() or [""]

        # Measure every line so we can size the box
        line_sizes = [
            cv.getTextSize(line or " ", font, font_scale, thickness) for line in lines
        ]
        max_text_w = max(tw for (tw, _), _ in line_sizes)
        total_text_h = sum(th + bl for (_, th), bl in line_sizes)
        total_text_h += line_gap * (len(lines) - 1)

        # Box geometry
        box_w = max_text_w + padding * 2
        box_h = total_text_h + padding * 2
        x1 = (frame_w - box_w) // 2
        y1 = (frame_h - box_h) // 2
        x2 = x1 + box_w
        y2 = y1 + box_h

        # Semi-transparent filled rectangle
        overlay = frame.copy()
        cv.rectangle(overlay, (x1, y1), (x2, y2), bg_color, thickness=cv.FILLED)
        # Subtle border for definition
        cv.rectangle(overlay, (x1, y1), (x2, y2), (120, 120, 120), thickness=1)
        cv.addWeighted(overlay, bg_alpha, frame, 1.0 - bg_alpha, 0, frame)

        # Draw each line of text, centered horizontally
        cursor_y = y1 + padding
        for line, ((tw, th), bl) in zip(lines, line_sizes):
            text_x = (frame_w - tw) // 2
            cursor_y += th
            cv.putText(
                frame,
                line,
                (text_x, cursor_y),
                font,
                font_scale,
                text_color,
                thickness,
                cv.LINE_AA,
            )
            cursor_y += bl + line_gap

        return frame
