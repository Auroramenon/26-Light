"""多模态特征融合 — 科学化风险映射 + EMA 时间平滑"""

import numpy as np


def _piecewise_linear(value, low, high):
    """分段线性映射: value < low → 0, value > high → 1, 中间线性插值"""
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return (value - low) / (high - low)


def normalize_hrv_score(hrv_features):
    """将 HRV 特征转换为 [0, 1] 疲劳评分（值越高越疲劳）

    疲劳时 HRV 特征表现：
    - RMSSD 降低 (正常 20-50ms, 疲劳 < 20ms)
    - SDNN 降低 (正常 50-100ms, 疲劳 < 30ms)
    - LF/HF 升高 (交感神经兴奋, 正常 0.5-2.0, 疲劳 > 3.0)
    """
    rmssd = hrv_features.get("rmssd", 30.0)
    sdnn = hrv_features.get("sdnn", 50.0)
    lf_hf = hrv_features.get("lf_hf", 1.0)

    # RMSSD 评分：< 15ms 高疲劳，> 40ms 正常
    rmssd_score = np.clip(1.0 - (rmssd - 15.0) / 25.0, 0, 1)
    # SDNN 评分：< 25ms 高疲劳，> 80ms 正常
    sdnn_score = np.clip(1.0 - (sdnn - 25.0) / 55.0, 0, 1)
    # LF/HF 评分：> 4.0 高疲劳，< 1.0 正常
    lfhf_score = np.clip((lf_hf - 1.0) / 3.0, 0, 1)

    return float(rmssd_score * 0.4 + sdnn_score * 0.3 + lfhf_score * 0.3)


class FeatureFuser:
    """带 EMA 平滑的多模态融合器"""

    def __init__(self, config):
        self.cfg = config
        self.alpha = config.get("ema_alpha", 0.3)
        self._prev_score = None

    def fuse(self, hrv_features, perclos, yawn_rate, head_pitch):
        """多模态特征加权融合 + EMA 平滑

        Returns:
            fatigue_score: [0, 1] 平滑后的综合疲劳评分
            risks: dict 各路独立风险分 (供分类器多证据判定)
        """
        cfg = self.cfg

        # --- 各路风险映射（分段线性） ---
        risk_hrv = normalize_hrv_score(hrv_features)

        risk_perclos = _piecewise_linear(
            perclos, cfg.get("perclos_low", 0.15), cfg.get("perclos_high", 0.30))

        risk_yawn = _piecewise_linear(
            yawn_rate, cfg.get("yawn_rate_low", 0.2), cfg.get("yawn_rate_high", 1.0))

        risk_head = _piecewise_linear(
            abs(head_pitch), cfg.get("head_angle_low", 15.0), cfg.get("head_angle_high", 35.0))

        # --- 加权融合 ---
        raw = (cfg["w_hrv"] * risk_hrv +
               cfg["w_perclos"] * risk_perclos +
               cfg["w_yawn"] * risk_yawn +
               cfg["w_head"] * risk_head)
        raw = float(np.clip(raw, 0, 1))

        # --- EMA 时间平滑 ---
        if self._prev_score is None:
            score = raw
        else:
            score = self.alpha * raw + (1.0 - self.alpha) * self._prev_score
        self._prev_score = score

        risks = {
            "hrv": risk_hrv,
            "perclos": risk_perclos,
            "yawn": risk_yawn,
            "head": risk_head,
        }
        return score, risks


# === 兼容旧接口 ===
def fuse_features(hrv_features, perclos, yawn_rate, head_pitch, config):
    """无状态兼容接口（不含 EMA，行为与旧版一致）"""
    cfg = config
    risk_hrv = normalize_hrv_score(hrv_features)
    risk_perclos = _piecewise_linear(
        perclos, cfg.get("perclos_low", 0.15), cfg.get("perclos_high", 0.30))
    risk_yawn = _piecewise_linear(
        yawn_rate, cfg.get("yawn_rate_low", 0.2), cfg.get("yawn_rate_high", 1.0))
    risk_head = _piecewise_linear(
        abs(head_pitch), cfg.get("head_angle_low", 15.0), cfg.get("head_angle_high", 35.0))

    total = (cfg["w_hrv"] * risk_hrv +
             cfg["w_perclos"] * risk_perclos +
             cfg["w_yawn"] * risk_yawn +
             cfg["w_head"] * risk_head)
    return float(np.clip(total, 0, 1))
