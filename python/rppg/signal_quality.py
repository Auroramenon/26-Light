"""BVP 信号质量指数 (SQI) 与模态置信度评估

用于置信度自适应多模态融合（专利要点二）：
实时评估 rPPG 脉搏波信号质量，并据此动态调整各模态在融合中的权重。

信号质量指数定义为脉搏频带内的"谱聚集度"——真实脉搏波在心率对应频点
附近能量高度集中，而运动伪影/照明干扰则表现为宽带噪声，谱能量分散。
因此以主峰邻域能量占带内总能量的比例作为 SQI，取值 [0, 1]，越大越可靠。

作者：26-Light项目组
"""

import numpy as np
from scipy.signal import welch


def compute_bvp_sqi(bvp, fs, band_low=0.7, band_high=2.5, peak_halfwidth_hz=0.2):
    """计算 BVP 信号质量指数 (Signal Quality Index)

    Args:
        bvp: 1D BVP 信号
        fs: 采样率 (fps)
        band_low: 脉搏频带下限 Hz
        band_high: 脉搏频带上限 Hz
        peak_halfwidth_hz: 主峰邻域半宽 Hz（用于统计峰值能量）

    Returns:
        sqi: float [0, 1]，谱聚集度；信号无效时返回 0
    """
    bvp = np.asarray(bvp, dtype=np.float64).ravel()
    if bvp.size < int(2 * fs) or np.std(bvp) < 1e-8:
        return 0.0

    nperseg = min(len(bvp), 256)
    f, psd = welch(bvp, fs=fs, nperseg=nperseg)

    band = (f >= band_low) & (f <= band_high)
    if not band.any():
        return 0.0

    band_power = float(np.trapz(psd[band], f[band]))
    if band_power <= 1e-12:
        return 0.0

    # 主峰及其邻域能量
    f_band = f[band]
    psd_band = psd[band]
    peak_idx = int(np.argmax(psd_band))
    peak_f = f_band[peak_idx]
    peak_mask = np.abs(f_band - peak_f) <= peak_halfwidth_hz
    peak_power = float(np.trapz(psd_band[peak_mask], f_band[peak_mask]))

    sqi = peak_power / band_power
    return float(np.clip(sqi, 0.0, 1.0))


def hrv_confidence(bvp_sqi, ibi_count, min_ibi_count=20, sqi_floor=0.25):
    """由 BVP 质量与 IBI 数量估计 HRV 通道置信度 [0, 1]

    HRV 依赖可靠的逐拍间期，因此同时要求：
    1) 谱质量 SQI 足够高（脉搏波清晰）
    2) 累积的 IBI 数量足够多（统计量稳定）

    Args:
        bvp_sqi: compute_bvp_sqi 的输出
        ibi_count: 当前累积的有效 IBI 个数
        min_ibi_count: 认为 IBI 统计充分所需的最小个数
        sqi_floor: SQI 低于该值时判定脉搏波不可信，置信度趋零

    Returns:
        conf: float [0, 1]
    """
    if bvp_sqi <= sqi_floor:
        sqi_term = 0.0
    else:
        sqi_term = (bvp_sqi - sqi_floor) / (1.0 - sqi_floor)

    count_term = np.clip(ibi_count / float(max(1, min_ibi_count)), 0.0, 1.0)
    return float(np.clip(sqi_term * count_term, 0.0, 1.0))


def behavior_confidence(landmarks_present, motion_level=0.0, motion_ref=25.0):
    """由关键点可用性与运动幅度估计行为通道置信度 [0, 1]

    行为指标（PERCLOS/哈欠/头姿）依赖人脸关键点。关键点缺失或剧烈运动
    （回头、遮挡）会显著降低其可靠性，此时应下调其融合权重。

    Args:
        landmarks_present: 本帧是否成功获得人脸关键点
        motion_level: 运动幅度指标（如 ROI 帧间平均差分），可选
        motion_ref: 运动幅度归一化参考值

    Returns:
        conf: float [0, 1]
    """
    if not landmarks_present:
        return 0.2  # 关键点缺失，保留极低置信度而非直接置零，避免完全丢失该路
    motion_penalty = np.clip(motion_level / max(1e-6, motion_ref), 0.0, 1.0)
    return float(np.clip(1.0 - 0.6 * motion_penalty, 0.2, 1.0))
