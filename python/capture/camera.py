"""LRCP S400 工业相机采集模块"""

import platform
import time

import cv2


class Camera:
    def __init__(self, config):
        self.cap = None
        self.backend_name = None
        self.index = config["camera_index"]

        self._open_capture(config)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["camera_height"])
        self.cap.set(cv2.CAP_PROP_FPS, config["camera_fps"])

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or config["camera_fps"]

    def _backend_candidates(self):
        if platform.system().lower() == "windows":
            return [
                ("DSHOW", cv2.CAP_DSHOW),
                ("MSMF", cv2.CAP_MSMF),
                ("ANY", cv2.CAP_ANY),
            ]
        return [("ANY", cv2.CAP_ANY)]

    def _open_capture(self, config):
        last_cap = None
        for backend_name, backend in self._backend_candidates():
            cap = cv2.VideoCapture(self.index, backend)
            last_cap = cap
            if cap.isOpened():
                self.cap = cap
                self.backend_name = backend_name
                return
            cap.release()

        raise RuntimeError(
            f"无法打开相机: {self.index}，已尝试后端: "
            f"{', '.join(name for name, _ in self._backend_candidates())}"
        )

    def read(self):
        """返回 (success, frame_bgr)"""
        for _ in range(5):
            ok, frame = self.cap.read()
            if ok and frame is not None:
                return ok, frame
            time.sleep(0.05)
        return False, None

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __del__(self):
        self.release()
