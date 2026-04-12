"""PERCLOS 眼部疲劳检测 — 基于 MediaPipe Face Mesh EAR"""

import collections
import numpy as np


# MediaPipe Face Mesh 眼部关键点索引
# 左眼: [362, 385, 387, 263, 373, 380]
# 右眼: [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]


def _eye_aspect_ratio(landmarks, eye_indices):
    """计算 Eye Aspect Ratio (EAR)"""
    pts = [landmarks[i] for i in eye_indices]
    # 垂直距离
    v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    # 水平距离
    h = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    if h < 1e-6:
        return 0.3
    return (v1 + v2) / (2.0 * h)


class EyeDetector:
    """PERCLOS 检测器：统计最近 N 秒内闭眼帧占比"""

    def __init__(self, config):
        self.threshold = config["ear_threshold"]
        window = int(config["perclos_window_sec"] * config["camera_fps"])
        self.history = collections.deque(maxlen=window)

    def update(self, face_landmarks):
        """输入 MediaPipe face_landmarks，返回当前 PERCLOS 值 [0, 1]

        Args:
            face_landmarks: MediaPipe FaceMesh 的 landmark 列表 (468 个点)
                            每个点为 (x, y, z) 归一化坐标

        Returns:
            perclos: 闭眼帧占比
        """
        if face_landmarks is None:
            self.history.append(False)
            return self.get_perclos()

        lm = [(p.x, p.y, p.z) for p in face_landmarks]

        ear_left = _eye_aspect_ratio(lm, LEFT_EYE)
        ear_right = _eye_aspect_ratio(lm, RIGHT_EYE)
        ear = (ear_left + ear_right) / 2.0

        is_closed = ear < self.threshold
        self.history.append(is_closed)
        return self.get_perclos()

    def get_perclos(self):
        if len(self.history) == 0:
            return 0.0
        return sum(self.history) / len(self.history)
