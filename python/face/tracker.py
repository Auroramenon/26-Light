"""KLT 光流人脸跟踪器 — 参考 heartbeat/RPPG.cpp"""

import cv2
import numpy as np


class FaceTracker:
    """在两次全量检测之间，用 KLT 光流跟踪人脸框"""

    def __init__(self, max_corners=10, quality=0.01, min_dist=25):
        self.max_corners = max_corners
        self.quality = quality
        self.min_dist = min_dist
        self.prev_gray = None
        self.corners = None
        self.box = None
        self._lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

    def init(self, frame_bgr, box):
        """用检测到的人脸框初始化跟踪"""
        self.box = list(box)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        self.prev_gray = gray
        self._detect_corners(gray, box)

    def update(self, frame_bgr):
        """用光流更新人脸框，返回 [x1,y1,x2,y2] 或 None"""
        if self.prev_gray is None or self.corners is None or len(self.corners) < 3:
            return None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # 前向光流
        new_pts, st_fwd, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, self.corners, None, **self._lk_params)
        # 反向光流验证
        back_pts, st_bwd, _ = cv2.calcOpticalFlowPyrLK(
            gray, self.prev_gray, new_pts, None, **self._lk_params)

        # 双向误差 < 2px 的点才保留
        diff = np.linalg.norm(self.corners - back_pts, axis=2).flatten()
        good = (st_fwd.flatten() == 1) & (st_bwd.flatten() == 1) & (diff < 2.0)

        if good.sum() < 3:
            self.prev_gray = gray
            return None

        old_good = self.corners[good]
        new_good = new_pts[good]

        # 用仿射变换估计人脸框位移
        dx = np.median(new_good[:, 0, 0] - old_good[:, 0, 0])
        dy = np.median(new_good[:, 0, 1] - old_good[:, 0, 1])

        self.box[0] += int(dx)
        self.box[1] += int(dy)
        self.box[2] += int(dx)
        self.box[3] += int(dy)

        self.corners = new_good.reshape(-1, 1, 2)
        self.prev_gray = gray
        return list(self.box)

    def _detect_corners(self, gray, box):
        """在人脸框内检测角点"""
        x1, y1, x2, y2 = box
        mask = np.zeros(gray.shape, dtype=np.uint8)
        # 梯形区域（前额+脸颊，排除嘴巴和下巴）
        w, h = x2 - x1, y2 - y1
        rx1, ry1 = int(x1 + 0.22 * w), int(y1 + 0.21 * h)
        rx2, ry2 = int(x1 + 0.78 * w), int(y1 + 0.65 * h)
        mask[ry1:ry2, rx1:rx2] = 255

        corners = cv2.goodFeaturesToTrack(
            gray, self.max_corners, self.quality, self.min_dist, mask=mask)
        self.corners = corners
