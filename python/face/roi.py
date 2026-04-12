"""前额 ROI 提取"""

import numpy as np


def extract_roi(frame_bgr, box, config):
    """从人脸框中提取前额 ROI 区域

    Args:
        frame_bgr: BGR 图像
        box: [x1, y1, x2, y2] 人脸框
        config: 配置字典，包含 roi_x_start/end, roi_y_start/end

    Returns:
        roi: BGR ROI 图像，若区域无效则返回 None
    """
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None

    rx1 = int(x1 + config["roi_x_start"] * w)
    rx2 = int(x1 + config["roi_x_end"] * w)
    ry1 = int(y1 + config["roi_y_start"] * h)
    ry2 = int(y1 + config["roi_y_end"] * h)

    # 边界检查
    H, W = frame_bgr.shape[:2]
    rx1, ry1 = max(0, rx1), max(0, ry1)
    rx2, ry2 = min(W, rx2), min(H, ry2)

    if rx2 - rx1 < 4 or ry2 - ry1 < 4:
        return None

    return frame_bgr[ry1:ry2, rx1:rx2].copy()


def get_roi_coords(box, config, img_shape):
    """返回 ROI 的绝对坐标 (rx1, ry1, rx2, ry2)，用于 GUI 绘制"""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    H, W = img_shape[:2]
    rx1 = max(0, int(x1 + config["roi_x_start"] * w))
    ry1 = max(0, int(y1 + config["roi_y_start"] * h))
    rx2 = min(W, int(x1 + config["roi_x_end"] * w))
    ry2 = min(H, int(y1 + config["roi_y_end"] * h))
    return rx1, ry1, rx2, ry2
