"""HRV 特征分析 — 从 BVP 信号提取时域和频域 HRV 指标"""

import numpy as np
from scipy.signal import find_peaks, butter, filtfilt, welch


def compute_hrv(bvp, fs):
    """从 BVP 信号计算 HRV 特征

    Args:
        bvp: 1D BVP 信号
        fs: 采样率

    Returns:
        dict: {rmssd, sdnn, pnn50, lf_hf, mean_hr}
    """
    if len(bvp) < 30:
        return _empty_hrv()

    # 带通滤波
    nyq = fs / 2
    b, a = butter(2, [0.7 / nyq, 4.0 / nyq], btype="bandpass")
    bvp_filt = filtfilt(b, a, bvp.astype(np.float64))

    # 寻峰 — 最小间距 0.33s (180 BPM)
    min_dist = int(fs * 0.33)
    peaks, _ = find_peaks(bvp_filt, distance=min_dist)

    if len(peaks) < 4:
        return _empty_hrv()

    # IBI (ms)
    ibi = np.diff(peaks) / fs * 1000.0

    # 过滤异常 IBI (< 300ms 或 > 1500ms)
    valid = (ibi > 300) & (ibi < 1500)
    ibi = ibi[valid]
    if len(ibi) < 3:
        return _empty_hrv()

    # 时域指标
    rmssd = float(np.sqrt(np.mean(np.diff(ibi) ** 2)))
    sdnn = float(np.std(ibi, ddof=1))
    nn50 = int(np.sum(np.abs(np.diff(ibi)) > 50))
    pnn50 = nn50 / len(ibi) * 100.0
    mean_hr = 60000.0 / np.mean(ibi)

    # 频域指标 (LF/HF)
    lf_hf = _compute_lf_hf(ibi)

    return {
        "rmssd": rmssd,
        "sdnn": sdnn,
        "pnn50": pnn50,
        "lf_hf": lf_hf,
        "mean_hr": mean_hr,
    }


def _compute_lf_hf(ibi_ms):
    """从 IBI 序列计算 LF/HF 比值"""
    if len(ibi_ms) < 8:
        return 1.0

    # 均匀重采样 IBI 到 4 Hz
    resample_fs = 4.0
    t = np.cumsum(ibi_ms) / 1000.0
    t = t - t[0]
    t_uniform = np.arange(0, t[-1], 1.0 / resample_fs)
    ibi_interp = np.interp(t_uniform, t, ibi_ms)

    # 去均值
    ibi_interp = ibi_interp - np.mean(ibi_interp)

    if len(ibi_interp) < 16:
        return 1.0

    # Welch PSD
    f, psd = welch(ibi_interp, fs=resample_fs, nperseg=min(len(ibi_interp), 256))

    # LF: 0.04-0.15 Hz, HF: 0.15-0.4 Hz
    lf_mask = (f >= 0.04) & (f < 0.15)
    hf_mask = (f >= 0.15) & (f < 0.4)

    lf_power = np.trapz(psd[lf_mask], f[lf_mask]) if lf_mask.any() else 0
    hf_power = np.trapz(psd[hf_mask], f[hf_mask]) if hf_mask.any() else 0

    if hf_power < 1e-10:
        return 1.0
    return float(lf_power / hf_power)


def _empty_hrv():
    return {"rmssd": 0.0, "sdnn": 0.0, "pnn50": 0.0, "lf_hf": 1.0, "mean_hr": 0.0}
