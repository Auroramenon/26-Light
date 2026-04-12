"""多模态特征融合"""

import numpy as np


def normalize_hrv_score(hrv_features):
    """将 HRV 特征转换为 [0, 1] 疲劳评分（值越高越疲劳）

    疲劳时 HRV 特征表现：
    - RMSSD 降低 (正常 20-50ms, 疲劳 < 20ms)
    - SDNN 降低 (正常 50-100ms, 疲劳 < 30ms)
    - pNN50 降低
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

    return (rmssd_score * 0.4 + sdnn_score * 0.3 + lfhf_score * 0.3)


def fuse_features(hrv_features, perclos, yawn_rate, head_pitch, config):
    """多模态特征加权融合

    Args:
        hrv_features: dict from hrv_analyzer
        perclos: [0, 1] 闭眼比例
        yawn_rate: 每分钟哈欠次数
        head_pitch: 俯仰角（度）
        config: 配置字典

    Returns:
        fatigue_score: [0, 1] 综合疲劳评分
    """
    hrv_score = normalize_hrv_score(hrv_features)

    # PERCLOS: > 0.4 为严重疲劳
    perclos_score = np.clip(perclos / 0.4, 0, 1)

    # 哈欠: > 5 次/分钟为严重
    yawn_score = np.clip(yawn_rate / 5.0, 0, 1)

    # 头部: 俯仰角超过阈值
    threshold = config["head_pitch_threshold"]
    head_score = np.clip(max(abs(head_pitch) - threshold, 0) / 20.0, 0, 1)

    total = (config["w_hrv"] * hrv_score +
             config["w_perclos"] * perclos_score +
             config["w_yawn"] * yawn_score +
             config["w_head"] * head_score)

    return float(np.clip(total, 0, 1))
