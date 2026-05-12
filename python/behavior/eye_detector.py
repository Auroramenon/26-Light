"""PERCLOS 眼部疲劳检测 — 基于 MediaPipe Face Mesh EAR"""

import collections
import numpy as np


# MediaPipe Face Mesh 眼部关键点索引
# 左眼: [362, 385, 387, 263, 373, 380]
# 右眼: [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]


def _rotate_pts_2d(pts, roll_rad):
    """将归一化 landmark 坐标绕图像中心旋转 roll_rad（逆时针）"""
    c, s = np.cos(roll_rad), np.sin(roll_rad)
    R = np.array([[c, -s], [s, c]])
    center = np.array([0.5, 0.5])
    rotated = []
    for p in pts:
        xy = np.array([p[0], p[1]]) - center
        xy_rot = R @ xy + center
        rotated.append((xy_rot[0], xy_rot[1], p[2]))
    return rotated


def _eye_aspect_ratio(landmarks, eye_indices, roll_rad=0.0):
    """计算 Eye Aspect Ratio (EAR)，支持摄像头 roll 角补偿"""
    pts = [landmarks[i] for i in eye_indices]
    if roll_rad != 0.0:
        pts = _rotate_pts_2d(pts, roll_rad)
    # 垂直距离（只用 x、y，z 不参与）
    v1 = np.linalg.norm(np.array(pts[1][:2]) - np.array(pts[5][:2]))
    v2 = np.linalg.norm(np.array(pts[2][:2]) - np.array(pts[4][:2]))
    # 水平距离
    h = np.linalg.norm(np.array(pts[0][:2]) - np.array(pts[3][:2]))
    if h < 1e-6:
        return 0.3
    return (v1 + v2) / (2.0 * h)


class EyeDetector:
    """PERCLOS 检测器：统计最近 N 秒内闭眼帧占比，支持摄像头 roll 角补偿"""

    def __init__(self, config):
        self.threshold = config["ear_threshold"]
        window = int(config["perclos_window_sec"] * config["camera_fps"])
        self.history = collections.deque(maxlen=window)
        # 至少积累 15 秒的有效帧（成功检测人脸的帧）才输出 PERCLOS
        self._min_samples = int(15 * config["camera_fps"])
        # 摄像头 roll 安装角（弧度），用于旋转 landmark 坐标对齐眼睛开合方向
        self._roll_rad = np.radians(config.get("camera_roll_offset", 0.0))

    def update(self, face_landmarks):
        """输入 MediaPipe face_landmarks，返回当前 PERCLOS 值 [0, 1]

        Args:
            face_landmarks: MediaPipe FaceMesh 的 landmark 列表 (468 个点)
                            每个点为 (x, y, z) 归一化坐标
                            传入 None 时跳过本帧（不追加，避免稀释 PERCLOS）

        Returns:
            perclos: 闭眼帧占比（仅基于成功检测到人脸的帧）
        """
        if face_landmarks is None:
            # 无检测帧不追加，保证 PERCLOS 只统计有效帧
            return self.get_perclos()

        lm = [(p.x, p.y, p.z) for p in face_landmarks]

        ear_left = _eye_aspect_ratio(lm, LEFT_EYE, self._roll_rad)
        ear_right = _eye_aspect_ratio(lm, RIGHT_EYE, self._roll_rad)
        ear = (ear_left + ear_right) / 2.0

        is_closed = ear < self.threshold
        self.history.append(is_closed)
        return self.get_perclos()

    def get_perclos(self):
        if len(self.history) < self._min_samples:
            return 0.0
        return sum(self.history) / len(self.history)
