"""FFT 心率估计 — 复用 rPPG-Toolbox 的 post_process"""

import sys
import os
import numpy as np
from scipy.signal import butter, filtfilt

_toolbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox"))
if _toolbox_path not in sys.path:
    sys.path.insert(0, _toolbox_path)

from evaluation.post_process import _calculate_fft_hr, _detrend


def estimate_hr(bvp, fs, low=0.7, high=4.0):
    """从 BVP 信号估计心率 (BPM)

    Args:
        bvp: 1D BVP 信号
        fs: 采样率
        low: 带通下限 Hz (0.7 = 42 BPM)
        high: 带通上限 Hz (4.0 = 240 BPM)

    Returns:
        hr_bpm: 心率 (BPM)
    """
    if len(bvp) < 30:
        return 0.0

    # 去趋势
    bvp = _detrend(bvp, 100)

    # 带通滤波
    nyq = fs / 2
    b, a = butter(2, [low / nyq, high / nyq], btype="bandpass")
    bvp = filtfilt(b, a, bvp.astype(np.float64))

    # FFT 心率
    hr = _calculate_fft_hr(bvp, fs=fs, low_pass=low, high_pass=high)
    return float(hr)
