"""人脸检测模块 — 封装 YOLO5Face 和 Haar Cascade"""

import sys
import os
import cv2
import numpy as np


class FaceDetector:
    def __init__(self, config):
        self.backend = config["face_det_backend"]
        self.enlarge = config["face_enlarge_ratio"]

        if self.backend == "Y5F":
            toolbox = config.get("_toolbox_path", os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox")))
            if toolbox not in sys.path:
                sys.path.insert(0, toolbox)
            from dataset.data_loader.face_detector.YOLO5Face import YOLO5Face
            self._yolo = YOLO5Face(backend="Y5F", device=config["device"])
        else:
            cascade_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox",
                "dataset", "haarcascade_frontalface_default.xml")
            if not os.path.exists(cascade_path):
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)

    def detect(self, frame_bgr):
        """检测最大人脸，返回 [x1, y1, x2, y2] 或 None"""
        if self.backend == "Y5F":
            return self._detect_yolo(frame_bgr)
        return self._detect_haar(frame_bgr)

    def _detect_yolo(self, frame):
        res = self._yolo.detect_face(frame)
        if res is None:
            return None
        return self._enlarge_box(res, frame.shape[:2])

    def _detect_haar(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        if len(faces) == 0:
            return None
        # 取最大人脸
        areas = [w * h for (_, _, w, h) in faces]
        idx = int(np.argmax(areas))
        x, y, w, h = faces[idx]
        box = [x, y, x + w, y + h]
        return self._enlarge_box(box, frame.shape[:2])

    def _enlarge_box(self, box, img_hw):
        """按 enlarge_ratio 放大人脸框，并裁剪到图像边界"""
        x1, y1, x2, y2 = box
        h, w = img_hw
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        bw, bh = (x2 - x1) * self.enlarge / 2, (y2 - y1) * self.enlarge / 2
        return [
            max(0, int(cx - bw)),
            max(0, int(cy - bh)),
            min(w, int(cx + bw)),
            min(h, int(cy + bh)),
        ]
