"""滑动窗口 ROI 帧缓冲区"""

import collections
import numpy as np


class SignalBuffer:
    """存储最近 N 帧的 ROI 图像，供 rPPG 算法使用"""

    def __init__(self, fps, window_sec):
        self.max_len = int(fps * window_sec)
        self.buffer = collections.deque(maxlen=self.max_len)

    def append(self, roi_bgr):
        """添加一帧 ROI (BGR)，内部转为 RGB"""
        roi_rgb = roi_bgr[:, :, ::-1].copy()  # BGR -> RGB
        self.buffer.append(roi_rgb)

    def is_ready(self):
        """缓冲区是否已满（至少积累了一个完整窗口）"""
        return len(self.buffer) >= self.max_len

    def get_frames(self):
        """返回 (N, H, W, 3) RGB 帧数组"""
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()

    def __len__(self):
        return len(self.buffer)
