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
    """头部姿态估计，输出相对于驾驶员正视方向的俯仰角 (pitch)"""

    def __init__(self, config):
        self.threshold = config.get("head_angle_low", config.get("head_pitch_threshold", 15.0))
        # 摄像头安装角补偿：从测量值中减去安装偏置，还原真实头部角度
        self._pitch_offset = config.get("camera_pitch_offset", 0.0)
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

        # 由于人脸3D模型坐标系与相机坐标系存在~180°偏置，
        # RQDecomp3x3返回的angles[0]在正面时约为±180°而非0°。
        # 将其归一化：正面→0°，低头→正值，抬头→负值。
        raw = angles[0]
        if raw > 90:
            pitch = -(raw - 180)
        elif raw < -90:
            pitch = -(raw + 180)
        else:
            pitch = -raw

        # 减去摄像头安装仰角，得到相对于驾驶员正视方向的真实俯仰角
        pitch -= self._pitch_offset
        return float(pitch)
