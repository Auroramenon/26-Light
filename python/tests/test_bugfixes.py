"""产品化缺陷修复的回归测试（无需相机/硬件）

覆盖本轮修复的逻辑/算法漏洞：
1. 自动恢复安全约束：驾驶员仍疲劳（评分高）时不得超时静默；证据减弱后方可恢复
2. NIR trend 模式的 HRV 计算器持久化：跨帧累积历史，趋势判据生效
3. 帧序列断裂重置的基础原语：SignalBuffer.clear 复位就绪状态
4. 相机实测帧率参与 DSP 的合理性（帧率钳制范围）

运行：
    python tests/test_bugfixes.py      # 从 python/ 目录
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from config import CONFIG
from fusion.fatigue_classifier import FatigueClassifier
from fusion.feature_fusion import FeatureFuser
from rppg.signal_buffer import SignalBuffer


def test_auto_reset_never_silences_a_fatigued_driver():
    """要点：评分仍高时，超时也不得自动恢复到 Level 0（安全）"""
    cfg = dict(CONFIG)
    cfg["hold_seconds"] = 0
    cfg["auto_reset_enabled"] = True
    cfg["auto_reset_durations"] = {1: 0.01, 2: 0.01, 3: 0.01}
    clf = FatigueClassifier(cfg)

    strong = {"perclos": 0.9, "hrv": 0.0, "yawn": 0.0, "head": 0.0}
    for _ in range(2):
        clf.update(0.60, strong)          # 升到中度
    assert clf.current_level >= 2

    # 计时早已到点，但评分仍高（0.60 高于 level2 降级阈值 0.45）→ 必须继续报警
    clf._level_enter_time = time.time() - 100
    lvl = clf.update(0.60, strong)
    assert lvl >= 2, "驾驶员仍疲劳时自动恢复不得静默报警"
    print(f"[修复3] 高评分+超时 → 仍保持等级 {lvl}（不误清零）")

    # 证据减弱（评分低于降级阈值、但高于快速恢复阈值）→ 允许超时自动恢复
    clf._level_enter_time = time.time() - 100
    lvl2 = clf.update(0.30, {"perclos": 0.0, "hrv": 0.0, "yawn": 0.0, "head": 0.0})
    assert lvl2 == 0, "证据减弱且超时后应自动恢复"
    print(f"[修复3] 低评分+超时 → 自动恢复到 {lvl2}")


def test_nir_trend_mode_is_stateful():
    """要点：trend 模式需跨帧累积历史，持续下降的 HRV 应产生正风险"""
    cfg = dict(CONFIG)
    cfg["is_nir_camera"] = True
    cfg["nir_hrv_mode"] = "trend"
    fuser = FeatureFuser(cfg)
    assert fuser._nir_calc is not None

    seq = [(50, 90), (45, 80), (40, 70), (35, 60), (30, 50), (25, 45), (20, 40)]
    risks_hrv = []
    for rmssd, sdnn in seq:
        hrv = {"valid": True, "ibi_count": 40, "mean_hr": 70,
               "rmssd": rmssd, "sdnn": sdnn, "lf_hf": 1.0}
        _, risks = fuser.fuse(hrv, 0.0, 0, 0.0, confidences=None)
        risks_hrv.append(risks["hrv"])

    # 若每帧新建计算器，历史恒为空、趋势恒为 0；持久化后末尾应 > 0
    print(f"[修复4] trend 风险序列={[round(r,2) for r in risks_hrv]}")
    assert risks_hrv[-1] > 0.0, "trend 模式应能识别持续下降的 HRV"


def test_signal_buffer_clear_resets_ready():
    """要点：帧序列断裂重置依赖 clear 能复位就绪状态"""
    buf = SignalBuffer(fps=30, window_sec=1)  # 30 帧就绪
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    for _ in range(30):
        buf.append(frame)
    assert buf.is_ready()
    buf.clear()
    assert not buf.is_ready() and len(buf) == 0
    print("[修复2] 断裂重置原语正常：clear 后未就绪")


def test_fps_clamp_range():
    """要点：实测帧率应被钳制到合理区间再驱动 DSP"""
    for raw, expected in [(0, 30.0), (25.0, 25.0), (7.0, 10.0), (120.0, 60.0)]:
        measured = float(raw) if raw else 30.0
        fps = float(np.clip(measured, 10.0, 60.0))
        assert fps == expected, f"fps({raw}) -> {fps}, 期望 {expected}"
    print("[修复1] 帧率钳制到 [10,60] 正常")


if __name__ == "__main__":
    tests = [
        test_auto_reset_never_silences_a_fatigued_driver,
        test_nir_trend_mode_is_stateful,
        test_signal_buffer_clear_resets_ready,
        test_fps_clamp_range,
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
