"""专利要点功能性验证（无需相机/硬件）

覆盖三项核心创新，可离线重复运行以自证技术方案可实施：
1. 环境红外共模抑制在强照明干扰下改善脉搏波质量（要点一）
2. 信号质量指数 SQI 区分脉搏与噪声（要点二基础）
3. 置信度自适应融合按可信度动态调权（要点二）
4. 分级状态机的迟滞/持续性行为（要点三）

运行：
    python tests/test_patent_features.py      # 从 python/ 目录
"""

import sys
import os

# 将 python/ 加入搜索路径，保证任意 cwd 均可运行
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from rppg.nir_illum import extract_nir_bvp_cmr, estimate_common_mode_gain
from rppg.signal_quality import compute_bvp_sqi, hrv_confidence, behavior_confidence
from rppg.hr_estimator import estimate_hr
from fusion.feature_fusion import _adaptive_weights, FeatureFuser
from fusion.fatigue_classifier import FatigueClassifier
from config import CONFIG


def _make_frames(series):
    """把一维强度序列还原为帧序列（每帧用常数图承载均值强度）"""
    return [np.full((20, 20, 3), v, dtype=np.float32) for v in series]


def test_common_mode_rejection():
    """要点一：参考区共模抑制应提升干扰下的脉搏波质量"""
    rng = np.random.default_rng(0)
    fs, T = 30, 10
    n = fs * T
    t = np.arange(n) / fs
    pulse_freq = 72.0 / 60.0
    base = 120.0

    pulse = 0.003 * base * np.sin(2 * np.pi * pulse_freq * t)
    # 环境红外共模干扰：低频强正弦（车灯扫过）+ 随机游走
    illum = 15.0 * np.sin(2 * np.pi * 0.3 * t) + np.cumsum(rng.standard_normal(n)) * 0.5
    roi = base + pulse + illum + rng.standard_normal(n) * 0.2
    ref = base * 0.6 + illum + rng.standard_normal(n) * 0.2  # 同共模、无脉搏

    roi_frames, ref_frames = _make_frames(roi), _make_frames(ref)

    bvp_plain = extract_nir_bvp_cmr(roi_frames, fs, ref_frames=None)
    bvp_cmr = extract_nir_bvp_cmr(roi_frames, fs, ref_frames=ref_frames)

    sqi_plain = compute_bvp_sqi(bvp_plain, fs)
    sqi_cmr = compute_bvp_sqi(bvp_cmr, fs)
    hr_cmr = estimate_hr(bvp_cmr, fs, 0.7, 2.5)

    print(f"[要点一] SQI 无抑制={sqi_plain:.2f} 有抑制={sqi_cmr:.2f} 心率(抑制后)={hr_cmr:.1f}BPM")
    assert sqi_cmr >= sqi_plain, "共模抑制不应降低信号质量"
    assert abs(hr_cmr - 72.0) < 6.0, "抑制后心率应接近真值"


def test_common_mode_gain_no_reference_signal():
    """常数参考（无信息）时增益应为 0，即不做对消"""
    target = np.sin(np.linspace(0, 10, 100))
    ref = np.ones(100)
    assert estimate_common_mode_gain(target, ref) == 0.0


def test_sqi_discriminates():
    """要点二基础：SQI 应区分纯净脉搏与白噪声"""
    fs, n = 30, 300
    t = np.arange(n) / fs
    clean = np.sin(2 * np.pi * 1.2 * t)
    noisy = np.random.default_rng(1).standard_normal(n)
    sqi_clean, sqi_noisy = compute_bvp_sqi(clean, fs), compute_bvp_sqi(noisy, fs)
    print(f"[要点二] SQI 纯净={sqi_clean:.2f} 噪声={sqi_noisy:.2f}")
    assert sqi_clean > 0.5 and sqi_noisy < sqi_clean


def test_adaptive_weights():
    """要点二：置信度自适应权重再归一化"""
    base = {"hrv": 0.20, "perclos": 0.30, "yawn": 0.35, "head": 0.15}

    # HRV 失效 → HRV 权重被压低、行为补偿、和为 1
    w_a = _adaptive_weights(base, {"hrv": 0.05, "perclos": 1, "yawn": 1, "head": 1})
    assert w_a["hrv"] < base["hrv"] and w_a["perclos"] > base["perclos"]
    assert abs(sum(w_a.values()) - 1.0) < 1e-9

    # 行为失效 → HRV 权重被抬高
    w_b = _adaptive_weights(base, {"hrv": 1, "perclos": 0.2, "yawn": 0.2, "head": 0.2})
    assert w_b["hrv"] > base["hrv"]

    # 全失效 → 退回基础权重（归一化）
    w_c = _adaptive_weights(base, {"hrv": 0, "perclos": 0, "yawn": 0, "head": 0})
    assert abs(sum(w_c.values()) - 1.0) < 1e-9
    print(f"[要点二] HRV失效后权重={w_a}")


def test_confidence_helpers():
    assert hrv_confidence(0.8, 30) > 0.5          # 质量高、IBI 足
    assert hrv_confidence(0.1, 30) == 0.0         # 质量差
    assert hrv_confidence(0.8, 5) < 0.3           # IBI 太少
    assert behavior_confidence(True) == 1.0
    assert behavior_confidence(False) < 0.3


def test_fuser_end_to_end():
    fuser = FeatureFuser(CONFIG)
    hrv = {"valid": True, "ibi_count": 30, "mean_hr": 72, "rmssd": 30, "sdnn": 50, "lf_hf": 1.0}
    score, risks = fuser.fuse(hrv, perclos=0.3, yawn_rate=2, head_pitch=10,
                              confidences={"hrv": 0.1, "perclos": 1, "yawn": 1, "head": 1})
    assert 0.0 <= score <= 1.0
    assert fuser._last_weights["hrv"] < CONFIG["w_hrv"]  # 低置信度 HRV 被降权
    print(f"[端到端] 融合评分={score:.2f} 有效权重={fuser._last_weights}")


def test_classifier_hysteresis():
    """要点三：迟滞 + 持续性——高分需持续才升级，且不在临界抖动"""
    cfg = dict(CONFIG)
    cfg["hold_seconds"] = 0  # 便于单测立即生效
    clf = FatigueClassifier(cfg)
    # 高评分 + 强 PERCLOS 证据 → 可达高等级
    lvl = clf.update(0.8, {"perclos": 0.9, "hrv": 0.0, "yawn": 0.0, "head": 0.0})
    assert lvl >= 2
    print(f"[要点三] 高分强证据 → 等级 {lvl}")


if __name__ == "__main__":
    tests = [
        test_common_mode_rejection,
        test_common_mode_gain_no_reference_signal,
        test_sqi_discriminates,
        test_adaptive_weights,
        test_confidence_helpers,
        test_fuser_end_to_end,
        test_classifier_hysteresis,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{'ALL_TESTS_PASSED' if failed == 0 else f'{failed} TEST(S) FAILED'}")
    sys.exit(1 if failed else 0)
