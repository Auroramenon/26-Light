"""HRV 特征分析 — 从 BVP 信号提取时域和频域 HRV 指标

支持两种使用方式:
1. 无状态: compute_hrv(bvp, fs) — 直接从单段 BVP 计算（短窗口，频域不可靠）
2. 有状态: IBIAccumulator — 从短窗口 BVP 中提取 IBI 并累积到 60s 滑窗，
   频域指标（LF/HF）在长窗口下才有意义。
"""

import time
import numpy as np
from collections import deque
from scipy.signal import find_peaks, filtfilt, welch
from scipy.signal import butter as _scipy_butter

# 缓存带通滤波器系数，避免每次 _extract_ibi 调用都重新计算
_IBI_FILTER_CACHE: dict = {}


def _get_ibi_filter(fs):
    """按采样率缓存并返回 IBI 带通滤波器系数"""
    if fs not in _IBI_FILTER_CACHE:
        nyq = fs / 2
        _IBI_FILTER_CACHE[fs] = _scipy_butter(2, [0.7 / nyq, 4.0 / nyq], btype="bandpass")
    return _IBI_FILTER_CACHE[fs]


def _extract_ibi(bvp, fs):
    """从 BVP 信号提取 IBI 序列（毫秒）

    同时使用距离、幅度和显著性约束，减少噪声误判峰值。

    Returns:
        ibi_ms: ndarray of valid IBI values (ms), may be empty
    """
    if len(bvp) < 30:
        return np.array([])

    b, a = _get_ibi_filter(fs)
    bvp_filt = filtfilt(b, a, bvp.astype(np.float64))

    min_dist = int(fs * 0.33)
    sigma = np.std(bvp_filt)

    # 优先：带高度+显著性约束的检测，减少噪声峰误判
    peaks, _ = find_peaks(
        bvp_filt,
        distance=min_dist,
        height=np.mean(bvp_filt) + 0.3 * sigma,
        prominence=0.4 * sigma,
    )

    # 回退：约束过严时放宽为仅距离约束
    if len(peaks) < 2:
        peaks, _ = find_peaks(bvp_filt, distance=min_dist)

    if len(peaks) < 2:
        return np.array([])

    ibi = np.diff(peaks) / fs * 1000.0
    valid = (ibi > 300) & (ibi < 1500)
    return ibi[valid]


class IBIAccumulator:
    """IBI 滑窗累积器 — 从短窗口 BVP 中提取增量 IBI，累积到长窗口计算 HRV

    每次 feed_bvp 只提取 update_interval 秒内的新 IBI，避免 8s 滑动窗口
    重叠导致同一心跳被重复计入（原实现约虚高 8-10 倍）。

    用法:
        acc = IBIAccumulator(window_sec=60, update_interval=1.0)
        acc.feed_bvp(bvp, fs)
        hrv = acc.compute()
    """

    def __init__(self, window_sec=60, update_interval=1.0):
        self.window_sec = window_sec
        self.update_interval = update_interval
        self._ibi_buffer = deque()      # (timestamp, ibi_ms) pairs
        self._last_update = 0.0
        self._cached_hrv = _empty_hrv("not_ready")

    def feed_bvp(self, bvp, fs):
        """从短窗口 BVP 提取增量 IBI 并追加到滑窗。

        只取 BVP 末尾约 update_interval 秒的新片段进行峰值检测，
        用 2s lookback 保证边界峰值不遗漏，但只保留最新的 IBI。
        """
        now = time.time()

        # 计算新增片段长度
        n_new = max(1, int(self.update_interval * fs))
        # 额外回看 2s 保证边界附近的峰值能被检测到
        n_lookback = min(int(2.0 * fs), len(bvp) - n_new)
        n_analyze = n_new + max(0, n_lookback)

        segment = bvp[-n_analyze:] if n_analyze < len(bvp) else bvp
        ibi_arr = _extract_ibi(segment, fs)

        if len(ibi_arr) > 0:
            # 估算新片段内最多含多少个 IBI（200BPM上限）
            max_new_ibi = max(1, int(self.update_interval * 200 / 60))
            for val in ibi_arr[-max_new_ibi:]:
                self._ibi_buffer.append((now, float(val)))

        # 淘汰超出窗口的旧数据
        cutoff = now - self.window_sec
        while self._ibi_buffer and self._ibi_buffer[0][0] < cutoff:
            self._ibi_buffer.popleft()

        # 按间隔更新缓存
        if now - self._last_update >= self.update_interval:
            self._cached_hrv = self._compute_from_buffer()
            self._last_update = now

    def compute(self):
        """返回最近一次计算的 HRV 特征"""
        return self._cached_hrv

    def _compute_from_buffer(self):
        ibi_values = np.array([v for _, v in self._ibi_buffer])
        if len(ibi_values) < 3:
            return _empty_hrv("insufficient_ibi")

        # 时域指标
        rmssd = float(np.sqrt(np.mean(np.diff(ibi_values) ** 2)))
        sdnn = float(np.std(ibi_values, ddof=1))
        nn50 = int(np.sum(np.abs(np.diff(ibi_values)) > 50))
        pnn50 = nn50 / len(ibi_values) * 100.0
        mean_hr = 60000.0 / np.mean(ibi_values)

        # 频域指标 — 累积的 IBI 足够长，LF/HF 才有意义
        lf_hf = _compute_lf_hf(ibi_values)

        return {
            "rmssd": rmssd,
            "sdnn": sdnn,
            "pnn50": pnn50,
            "lf_hf": lf_hf,
            "mean_hr": mean_hr,
            "ibi_count": len(ibi_values),
            "valid": True,
            "reason": "ok",
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


def _empty_hrv(reason="unknown"):
    # 使用中性基线，避免窗口不足时把 HRV 风险误判为高疲劳。
    return {
        "rmssd": 30.0,
        "sdnn": 50.0,
        "pnn50": 10.0,
        "lf_hf": 1.0,
        "mean_hr": 0.0,
        "ibi_count": 0,
        "valid": False,
        "reason": reason,
    }


def compute_hrv(bvp, fs):
    """兼容旧接口 — 从单段 BVP 直接计算 HRV（短窗口，频域不够可靠）"""
    ibi = _extract_ibi(bvp, fs)
    if len(ibi) < 3:
        return _empty_hrv("insufficient_ibi")

    rmssd = float(np.sqrt(np.mean(np.diff(ibi) ** 2)))
    sdnn = float(np.std(ibi, ddof=1))
    nn50 = int(np.sum(np.abs(np.diff(ibi)) > 50))
    pnn50 = nn50 / len(ibi) * 100.0
    mean_hr = 60000.0 / np.mean(ibi)
    lf_hf = _compute_lf_hf(ibi)

    return {
        "rmssd": rmssd,
        "sdnn": sdnn,
        "pnn50": pnn50,
        "lf_hf": lf_hf,
        "mean_hr": mean_hr,
        "ibi_count": len(ibi),
        "valid": True,
        "reason": "ok",
    }
