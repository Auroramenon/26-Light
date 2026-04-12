"""打哈欠检测 — 基于 MediaPipe Face Mesh 嘴部 MAR"""

import collections
import time
import numpy as np

# MediaPipe Face Mesh 嘴部关键点
# 上唇: 13, 下唇: 14, 左嘴角: 78, 右嘴角: 308
# 上唇外: 82, 下唇外: 87 (用于更精确的 MAR)
MOUTH_TOP = 13
MOUTH_BOTTOM = 14
MOUTH_LEFT = 78
MOUTH_RIGHT = 308
MOUTH_TOP_INNER = 82
MOUTH_BOTTOM_INNER = 87


def _mouth_aspect_ratio(landmarks):
    """计算 Mouth Aspect Ratio (MAR)"""
    top = np.array((landmarks[MOUTH_TOP].x, landmarks[MOUTH_TOP].y))
    bottom = np.array((landmarks[MOUTH_BOTTOM].x, landmarks[MOUTH_BOTTOM].y))
    left = np.array((landmarks[MOUTH_LEFT].x, landmarks[MOUTH_LEFT].y))
    right = np.array((landmarks[MOUTH_RIGHT].x, landmarks[MOUTH_RIGHT].y))

    vertical = np.linalg.norm(top - bottom)
    horizontal = np.linalg.norm(left - right)

    if horizontal < 1e-6:
        return 0.0
    return vertical / horizontal


class YawnDetector:
    """哈欠检测器：统计每分钟哈欠次数"""

    def __init__(self, config):
        self.threshold = config["yawn_mar_threshold"]
        self.min_frames = config["yawn_min_frames"]
        self._consecutive = 0
        self._in_yawn = False
        # 记录最近60秒的哈欠时间戳
        self._yawn_times = collections.deque()
        self._window = 60.0  # 秒

    def update(self, face_landmarks):
        """输入 MediaPipe face_landmarks，返回每分钟哈欠次数

        Returns:
            yawn_rate: 每分钟哈欠次数
        """
        now = time.time()
        # 清理过期记录
        while self._yawn_times and now - self._yawn_times[0] > self._window:
            self._yawn_times.popleft()

        if face_landmarks is None:
            self._consecutive = 0
            self._in_yawn = False
            return self.get_yawn_rate()

        mar = _mouth_aspect_ratio(face_landmarks)

        if mar > self.threshold:
            self._consecutive += 1
            if self._consecutive >= self.min_frames and not self._in_yawn:
                self._in_yawn = True
                self._yawn_times.append(now)
        else:
            self._consecutive = 0
            self._in_yawn = False

        return self.get_yawn_rate()

    def get_yawn_rate(self):
        """返回每分钟哈欠次数"""
        return len(self._yawn_times)
