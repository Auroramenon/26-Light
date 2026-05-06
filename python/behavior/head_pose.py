"""头部姿态估计 — 基于 MediaPipe Face Mesh + solvePnP"""

import numpy as np
import cv2

# 用于 solvePnP 的 6 个关键点索引 (MediaPipe Face Mesh)
# 鼻尖, 下巴, 左眼外角, 右眼外角, 左嘴角, 右嘴角
POSE_LANDMARKS = [1, 152, 33, 263, 61, 291]

# 通用 3D 人脸模型坐标 (mm)
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # 鼻尖
    (0.0, -330.0, -65.0),     # 下巴
    (-225.0, 170.0, -135.0),  # 左眼外角
    (225.0, 170.0, -135.0),   # 右眼外角
    (-150.0, -150.0, -125.0), # 左嘴角
    (150.0, -150.0, -125.0),  # 右嘴角
], dtype=np.float64)


class HeadPoseEstimator:
    """头部姿态估计，输出俯仰角 (pitch)"""

    def __init__(self, config):
        # 兼容旧配置键: head_pitch_threshold
        self.threshold = config.get("head_angle_low", config.get("head_pitch_threshold", 15.0))
        self._camera_matrix = None
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    def update(self, face_landmarks, frame_shape):
        """估计头部俯仰角

        Args:
            face_landmarks: MediaPipe FaceMesh landmark 列表
            frame_shape: (H, W, C) 图像尺寸

        Returns:
            pitch: 俯仰角（度），正值=低头，负值=抬头
        """
        if face_landmarks is None:
            return 0.0

        h, w = frame_shape[:2]

        # 懒初始化相机内参（假设无畸变）
        if self._camera_matrix is None:
            focal = w
            self._camera_matrix = np.array([
                [focal, 0, w / 2],
                [0, focal, h / 2],
                [0, 0, 1],
            ], dtype=np.float64)

        # 提取 2D 关键点
        pts_2d = []
        for idx in POSE_LANDMARKS:
            lm = face_landmarks[idx]
            pts_2d.append((lm.x * w, lm.y * h))
        pts_2d = np.array(pts_2d, dtype=np.float64)

        # solvePnP
        success, rvec, tvec = cv2.solvePnP(
            MODEL_POINTS, pts_2d, self._camera_matrix, self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE)

        if not success:
            return 0.0

        # 旋转向量 -> 旋转矩阵 -> 欧拉角
        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

        pitch = angles[0]  # 俯仰角
        return float(pitch)
