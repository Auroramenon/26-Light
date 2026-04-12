"""LRCP S400 工业相机采集模块"""

import cv2


class Camera:
    def __init__(self, config):
        self.cap = cv2.VideoCapture(config["camera_index"])
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["camera_height"])
        self.cap.set(cv2.CAP_PROP_FPS, config["camera_fps"])
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开相机: {config['camera_index']}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or config["camera_fps"]

    def read(self):
        """返回 (success, frame_bgr)"""
        return self.cap.read()

    def release(self):
        self.cap.release()

    def __del__(self):
        self.release()
