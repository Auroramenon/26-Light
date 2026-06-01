"""FFT 心率估计 — 零填充 FFT + 汉宁窗，提升频率分辨率"""

import numpy as np
from scipy.signal import butter, filtfilt, detrend


def estimate_hr(bvp, fs, low=0.7, high=4.0):
    """从 BVP 信号估计心率 (BPM)

    使用零填充 FFT + 汉宁窗：
    - 8s@30fps 原始分辨率 0.125Hz(±7.5BPM)，8x 零填充后约 0.016Hz(±1BPM)
    - 汉宁窗抑制旁瓣泄漏，避免峰值频率偏移

    Args:
        bvp: 1D BVP 信号
        fs: 采样率
        low: 带通下限 Hz (0.7 = 42 BPM)
        high: 带通上限 Hz (4.0 = 240 BPM)

    Returns:
        hr_bpm: 心率 (BPM)，无效时返回 0.0
    """
    bvp = np.asarray(bvp, dtype=np.float64)
    if len(bvp) < 30:
        return 0.0

    # 去线性趋势
    bvp = detrend(bvp, type="linear")

    # 带通滤波
    nyq = fs / 2.0
    if low / nyq <= 0 or high / nyq >= 1.0:
        return 0.0
    b, a = butter(2, [low / nyq, high / nyq], btype="bandpass")
    bvp = filtfilt(b, a, bvp)

    # 汉宁窗 + 8x 零填充 FFT，大幅提升频率分辨率
    N = len(bvp)
    nfft = max(N * 8, 4096)
    window = np.hanning(N)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)
    power = np.abs(np.fft.rfft(bvp * window, n=nfft)) ** 2

    # 在生理范围内找峰值
    mask = (freqs >= low) & (freqs <= high)
    if not mask.any():
        return 0.0

    peak_freq = freqs[mask][np.argmax(power[mask])]
    hr = peak_freq * 60.0

    # 生理范围校验：正常人静息 40-180 BPM
    if hr < 40.0 or hr > 180.0:
        return 0.0

    return float(hr)
