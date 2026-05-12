"""近红外 rPPG 算法 - 单通道强度法

本模块实现基于近红外(850nm)成像的非接触式心率检测
适用于夜间低光照环境，配合850nm LED补光使用

原理：
- 血液中的血红蛋白在850nm波段仍有光吸收
- 心跳引起的血容量变化导致皮肤对850nm光的反射率产生微小变化(0.1-0.5%)
- 通过时域分析提取这种周期性变化，得到心率信息

作者：26-Light项目组
日期：2026-04
"""

import numpy as np
from scipy.signal import butter, filtfilt, detrend


def extract_nir_bvp(roi_frames, fs, bandpass_low=0.7, bandpass_high=4.0):
    """从近红外 ROI 帧序列提取 BVP 信号（基础版）

    Args:
        roi_frames: list of (H, W, 3) BGR 图像（近红外相机输出）
                    虽然是3通道，但在NIR模式下三通道值几乎相同
        fs: 采样率 (fps)
        bandpass_low: 带通下限 Hz (默认0.7 = 42 BPM)
        bandpass_high: 带通上限 Hz (默认4.0 = 240 BPM)

    Returns:
        bvp: 1D numpy array, 脉搏波信号
    """
    if len(roi_frames) < 30:
        # 信号太短，无法可靠提取
        return np.zeros(len(roi_frames))

    # 1. 提取单通道强度时间序列
    raw_signal = []
    for frame in roi_frames:
        # 转为灰度（平均三通道）
        gray = np.mean(frame, axis=2)  # (H, W)
        # 空间平均：整个ROI的平均亮度
        mean_intensity = np.mean(gray)
        raw_signal.append(mean_intensity)

    raw_signal = np.array(raw_signal)

    # 2. 去趋势（移除低频漂移）
    detrended = detrend(raw_signal, type='linear')

    # 3. 标准化
    if np.std(detrended) > 1e-6:
        normalized = (detrended - np.mean(detrended)) / np.std(detrended)
    else:
        normalized = detrended

    # 4. 带通滤波
    nyq = fs / 2.0
    low = bandpass_low / nyq
    high = bandpass_high / nyq

    if low <= 0 or high >= 1.0:
        return normalized

    b, a = butter(4, [low, high], btype='bandpass')
    bvp = filtfilt(b, a, normalized)

    return bvp


def extract_nir_bvp_advanced(roi_frames, fs, bandpass_low=0.7, bandpass_high=4.0):
    """从近红外 ROI 帧序列提取 BVP 信号（改进版）

    改进点：多区域加权平均 - 额头中央和太阳穴区域的血管信号更强

    Args:
        roi_frames: list of (H, W, 3) BGR 图像
        fs: 采样率 (fps)
        bandpass_low: 带通下限 Hz
        bandpass_high: 带通上限 Hz

    Returns:
        bvp: 1D numpy array, 脉搏波信号
    """
    if len(roi_frames) < 30:
        return np.zeros(len(roi_frames))

    signals = []

    for frame in roi_frames:
        gray = np.mean(frame, axis=2)
        H, W = gray.shape

        # 将ROI分为三个子区域
        left_temple = gray[:, :W//3]
        forehead_center = gray[:, W//3:2*W//3]
        right_temple = gray[:, 2*W//3:]

        # 加权平均（额头中央权重更高）
        weighted_signal = (
            0.25 * np.mean(left_temple) +
            0.50 * np.mean(forehead_center) +
            0.25 * np.mean(right_temple)
        )
        signals.append(weighted_signal)

    signals = np.array(signals)

    # 去趋势
    detrended = detrend(signals, type='linear')

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

    b, a = butter(4, [low, high], btype='bandpass')
    bvp = filtfilt(b, a, normalized)

    return bvp


def extract_nir_bvp_robust(roi_frames, fs, bandpass_low=0.7, bandpass_high=4.0):
    """从近红外 ROI 帧序列提取 BVP 信号（鲁棒版）

    额外改进：
    1. 运动伪影检测
    2. 自适应降权运动帧

    Args:
        roi_frames: list of (H, W, 3) BGR 图像
        fs: 采样率 (fps)
        bandpass_low: 带通下限 Hz
        bandpass_high: 带通上限 Hz

    Returns:
        bvp: 1D numpy array, 脉搏波信号
    """
    if len(roi_frames) < 30:
        return np.zeros(len(roi_frames))

    signals = []
    motion_scores = []

    prev_gray = None
    for frame in roi_frames:
        gray = np.mean(frame, axis=2)
        H, W = gray.shape

        # 多区域加权
        left = gray[:, :W//3]
        center = gray[:, W//3:2*W//3]
        right = gray[:, 2*W//3:]

        weighted = 0.25 * np.mean(left) + 0.50 * np.mean(center) + 0.25 * np.mean(right)
        signals.append(weighted)

        # 运动检测
        if prev_gray is not None:
            frame_diff = np.abs(gray - prev_gray)
            motion_score = np.mean(frame_diff)
            motion_scores.append(motion_score)
        else:
            motion_scores.append(0.0)

        prev_gray = gray.copy()

    signals = np.array(signals)
    motion_scores = np.array(motion_scores)

    # 运动伪影抑制：用线性插值替换运动帧，避免降权引入人为幅度跳变
    motion_threshold = np.percentile(motion_scores, 75)
    bad = motion_scores > motion_threshold
    if bad.any() and not bad.all():
        x_all = np.arange(len(signals))
        x_good = x_all[~bad]
        signals = np.interp(x_all, x_good, signals[~bad])

    detrended = detrend(signals, type='linear')

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

    b, a = butter(5, [low, high], btype='bandpass')
    bvp = filtfilt(b, a, normalized)

    return bvp
