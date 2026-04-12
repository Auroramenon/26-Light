"""无监督 rPPG 算法封装 — 调用 rPPG-Toolbox 的 CHROM / POS"""

import sys
import os
import numpy as np

# 将 rPPG-Toolbox 加入搜索路径
_toolbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox"))
if _toolbox_path not in sys.path:
    sys.path.insert(0, _toolbox_path)

from unsupervised_methods.methods.CHROME_DEHAAN import CHROME_DEHAAN
from unsupervised_methods.methods.POS_WANG import POS_WANG


def extract_bvp(roi_frames, fs, method="CHROM"):
    """从 ROI 帧序列提取 BVP 信号

    Args:
        roi_frames: list of (H, W, 3) RGB 图像
        fs: 采样率 (fps)
        method: "CHROM" 或 "POS"

    Returns:
        bvp: 1D numpy array, 脉搏波信号
    """
    if method == "CHROM":
        bvp = CHROME_DEHAAN(roi_frames, fs)
    elif method == "POS":
        bvp = POS_WANG(roi_frames, fs)
    else:
        raise ValueError(f"不支持的 rPPG 方法: {method}")

    return np.asarray(bvp).flatten()
