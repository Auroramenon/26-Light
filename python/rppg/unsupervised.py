"""无监督 rPPG 算法封装 — 支持 RGB 和 NIR 模式"""

import sys
import os
import numpy as np

# 导入近红外 rPPG 模块（总是可用）
from .nir_rppg import extract_nir_bvp, extract_nir_bvp_advanced, extract_nir_bvp_robust
from .nir_illum import extract_nir_bvp_cmr

# 尝试导入 rPPG-Toolbox（仅RGB模式需要）
_TOOLBOX_AVAILABLE = False
try:
    # 将 rPPG-Toolbox 加入搜索路径
    _toolbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox"))
    if _toolbox_path not in sys.path:
        sys.path.insert(0, _toolbox_path)

    from unsupervised_methods.methods.CHROME_DEHAAN import CHROME_DEHAAN
    from unsupervised_methods.methods.POS_WANG import POS_WANG
    _TOOLBOX_AVAILABLE = True
except ImportError as e:
    print(f"[警告] rPPG-Toolbox不可用: {e}")
    print(f"[提示] RGB模式(CHROM/POS)将不可用，但NIR模式正常工作")


def extract_bvp(roi_frames, fs, method="CHROM", is_nir=False, ref_frames=None):
    """从 ROI 帧序列提取 BVP 信号

    Args:
        roi_frames: list of (H, W, 3) RGB/NIR 图像
        fs: 采样率 (fps)
        method: "CHROM" / "POS" / "NIR" / "NIR_ADV" / "NIR_ROBUST" / "NIR_CMR"
        is_nir: 是否为近红外模式（自动选择NIR算法）
        ref_frames: 参考区帧序列（仅 NIR_CMR 环境红外共模抑制使用，可为 None）

    Returns:
        bvp: 1D numpy array, 脉搏波信号
    """
    # 近红外模式
    if is_nir or method.startswith("NIR"):
        if method == "NIR_CMR":
            return extract_nir_bvp_cmr(roi_frames, fs, ref_frames=ref_frames)
        elif method == "NIR_ROBUST":
            return extract_nir_bvp_robust(roi_frames, fs)
        elif method == "NIR_ADV":
            return extract_nir_bvp_advanced(roi_frames, fs)
        else:  # "NIR" 或 is_nir=True
            return extract_nir_bvp(roi_frames, fs)

    # 传统 RGB rPPG
    if not _TOOLBOX_AVAILABLE:
        raise RuntimeError(
            f"RGB rPPG方法 '{method}' 需要 rPPG-Toolbox，但导入失败。\n"
            f"请安装依赖: cd D:\\guangdian\\rPPG-Toolbox && pip install opencv-python scikit-image\n"
            f"或使用NIR模式: 设置 is_nir_camera=True 和 rppg_method='NIR_ADV'"
        )

    if method == "CHROM":
        bvp = CHROME_DEHAAN(roi_frames, fs)
    elif method == "POS":
        bvp = POS_WANG(roi_frames, fs)
    else:
        raise ValueError(f"不支持的 rPPG 方法: {method}")

    return np.asarray(bvp).flatten()
