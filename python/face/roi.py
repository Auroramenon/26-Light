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


def extract_reference_region(frame_bgr, box, config):
    """提取环境红外共模抑制所需的"参考区"（非灌注背景区）

    参考区取人脸框左右两侧、与人脸垂直中心齐平的背景条带。该区域与前额 ROI
    受到近似相同的环境红外照明变化（对向车灯/路灯/补光灯抖动），但几乎不含
    脉搏信号，因此可用于估计并对消灌注区中的共模照明干扰。

    为保证与 ROI 帧数一一对应且尺寸稳定，参考区被缩放/裁剪为与传入 ROI 相当
    的小块；若两侧空间不足则返回 None（此时共模抑制自动退化为加权强度法）。

    Args:
        frame_bgr: BGR 整帧图像
        box: [x1, y1, x2, y2] 人脸框
        config: 配置字典

    Returns:
        ref: BGR 参考区图像，若无法取得则返回 None
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    H, W = frame_bgr.shape[:2]
    fw, fh = x2 - x1, y2 - y1
    if fw <= 0 or fh <= 0:
        return None

    # 参考条带宽度取人脸宽度的一定比例
    strip_w = max(8, int(config.get("ref_strip_ratio", 0.25) * fw))
    # 垂直范围与人脸中部对齐
    ry1 = max(0, y1 + int(0.20 * fh))
    ry2 = min(H, y1 + int(0.80 * fh))
    if ry2 - ry1 < 4:
        return None

    patches = []
    # 左侧背景
    lx2 = x1
    lx1 = lx2 - strip_w
    if lx1 >= 0:
        patches.append(frame_bgr[ry1:ry2, lx1:lx2])
    # 右侧背景
    rx1 = x2
    rx2 = rx1 + strip_w
    if rx2 <= W:
        patches.append(frame_bgr[ry1:ry2, rx1:rx2])

    if not patches:
        return None

    # 拼接左右背景条带作为参考区（仅用于强度均值，形状无关紧要）
    min_h = min(p.shape[0] for p in patches)
    patches = [p[:min_h] for p in patches]
    return np.concatenate(patches, axis=1).copy()


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
