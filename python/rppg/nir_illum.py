"""车载近红外主动照明下的环境红外共模抑制 rPPG（专利要点一）

背景问题
--------
夜间行车时，对向车灯、路灯、隧道灯、以及自车 850nm 补光灯的抖动，都会在
近红外相机上引入大幅度的环境红外强度波动。这一干扰与心跳引起的皮肤反射率
微变（约 0.1%~0.5%）在同一强度信号中叠加，且幅度常高出脉搏信号 1~2 个数量级，
是夜间车载单通道 NIR-rPPG 心率检测失效的主要原因。传统 RGB rPPG（CHROM/POS）
依赖 R/G/B 三通道的色度差分来抑制光照，无法直接用于单通道近红外。

技术方案
--------
同步采集两个区域：
1. 灌注区（前额皮肤 ROI）——同时包含脉搏信号与环境红外共模干扰；
2. 参考区（人脸框外的非灌注背景/结构区域）——只含环境红外共模干扰，几乎不含脉搏。

两区域受到的环境红外照明变化近似相同（共模），而脉搏信号仅存在于灌注区。
以最小二乘估计参考信号对灌注信号的最优共模增益 a，从灌注信号中减去 a×参考信号，
即可对消环境红外干扰，保留脉搏成分（差模），再经去趋势/带通得到干净 BVP。

当参考帧不可用时，本方法自动退化为多区域加权强度法，保证鲁棒可用。

作者：26-Light项目组
日期：2026-07
"""

import numpy as np
from scipy.signal import butter, filtfilt, detrend


def _region_intensity_series(frames):
    """将帧序列压成一维强度时间序列（多区域加权，额头中央权重更高）"""
    series = []
    for frame in frames:
        gray = np.mean(frame, axis=2)
        W = gray.shape[1]
        left = gray[:, :W // 3]
        center = gray[:, W // 3:2 * W // 3]
        right = gray[:, 2 * W // 3:]
        series.append(0.25 * np.mean(left) + 0.50 * np.mean(center) + 0.25 * np.mean(right))
    return np.asarray(series, dtype=np.float64)


def _plain_intensity_series(frames):
    """将帧序列压成一维平均强度序列（用于参考区，不需要分区加权）"""
    return np.asarray([float(np.mean(f)) for f in frames], dtype=np.float64)


def estimate_common_mode_gain(target, reference):
    """以最小二乘估计参考信号对目标信号的最优共模增益 a

    在高通（去除各自直流基线）后求解 argmin_a ||target' - a*reference'||^2，
    解析解 a = <target', reference'> / <reference', reference'>。

    Returns:
        a: float，共模增益；参考能量过小时返回 0（视为无共模可对消）
    """
    t = target - np.mean(target)
    r = reference - np.mean(reference)
    denom = float(np.dot(r, r))
    if denom < 1e-9:
        return 0.0
    a = float(np.dot(t, r) / denom)
    # 限幅，避免病态参考导致过度对消
    return float(np.clip(a, -3.0, 3.0))


def extract_nir_bvp_cmr(roi_frames, fs, ref_frames=None,
                        bandpass_low=0.7, bandpass_high=2.5):
    """环境红外共模抑制的近红外 BVP 提取

    Args:
        roi_frames: 灌注区（前额 ROI）帧序列 list of (H, W, 3)
        fs: 采样率 (fps)
        ref_frames: 参考区（非灌注背景区）帧序列，可为 None（退化为加权强度法）
        bandpass_low/high: 带通范围 Hz

    Returns:
        bvp: 1D numpy array 脉搏波信号
    """
    if len(roi_frames) < 30:
        return np.zeros(len(roi_frames))

    roi_series = _region_intensity_series(roi_frames)

    # === 核心：环境红外共模抑制 ===
    if ref_frames is not None and len(ref_frames) == len(roi_frames):
        ref_series = _plain_intensity_series(ref_frames)
        a = estimate_common_mode_gain(roi_series, ref_series)
        # 从灌注信号中减去按最优增益缩放的参考信号，对消共模照明干扰
        signal = roi_series - a * ref_series
    else:
        # 参考不可用时退化：仅用灌注区多区域加权强度
        signal = roi_series

    # 去趋势（移除残余低频漂移）
    detrended = detrend(signal, type='linear')

    # 标准化
    if np.std(detrended) > 1e-6:
        normalized = (detrended - np.mean(detrended)) / np.std(detrended)
    else:
        normalized = detrended

    # 带通滤波
    nyq = fs / 2.0
    low = bandpass_low / nyq
    high = bandpass_high / nyq
    if low <= 0 or high >= 1.0:
        return normalized

    b, a_filt = butter(4, [low, high], btype='bandpass')
    return filtfilt(b, a_filt, normalized)
