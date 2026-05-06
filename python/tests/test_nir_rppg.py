"""NIR-rPPG 测试脚本

用于验证近红外rPPG功能是否正常工作

使用方法：
    python test_nir_rppg.py

测试内容：
1. 相机采集测试
2. NIR-rPPG信号提取测试
3. 心率计算测试
4. HRV风险评估测试

作者：26-Light项目组
"""

import sys
import os
import cv2
import numpy as np
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.roi import extract_roi
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.hr_estimator import estimate_hr
from rppg.hrv_analyzer import IBIAccumulator
from rppg.nir_hrv import NIRHRVRiskCalculator


def test_camera():
    """测试1：相机采集"""
    print("=" * 60)
    print("测试1：相机采集")
    print("=" * 60)

    try:
        camera = Camera(CONFIG)
        print(f"✓ 相机打开成功")
        print(f"  - 设备索引: {CONFIG['camera_index']}")
        print(f"  - 分辨率: {CONFIG['camera_width']}x{CONFIG['camera_height']}")
        print(f"  - 帧率: {camera.fps} FPS")

        # 采集几帧测试
        for i in range(5):
            success, frame = camera.read()
            if not success:
                print(f"✗ 第{i+1}帧采集失败")
                return False
            print(f"  - 第{i+1}帧: {frame.shape}, 平均亮度: {np.mean(frame):.1f}")

        camera.release()
        print("✓ 相机采集测试通过\n")
        return True

    except Exception as e:
        print(f"✗ 相机采集测试失败: {e}\n")
        return False


def test_nir_rppg():
    """测试2：NIR-rPPG信号提取"""
    print("=" * 60)
    print("测试2：NIR-rPPG信号提取")
    print("=" * 60)

    try:
        camera = Camera(CONFIG)
        detector = FaceDetector(CONFIG)
        signal_buffer = SignalBuffer(CONFIG["camera_fps"], CONFIG["signal_window_sec"])

        print(f"✓ 模块初始化成功")
        print(f"  - rPPG方法: {CONFIG['rppg_method']}")
        print(f"  - 信号窗口: {CONFIG['signal_window_sec']}秒")
        print(f"  - NIR模式: {CONFIG['is_nir_camera']}")

        print("\n开始采集信号...")
        print(f"需要采集 {CONFIG['signal_window_sec']}秒 ({int(CONFIG['camera_fps'] * CONFIG['signal_window_sec'])}帧)")

        frame_count = 0
        start_time = time.time()

        while not signal_buffer.is_ready():
            success, frame = camera.read()
            if not success:
                print("✗ 帧采集失败")
                return False

            # 人脸检测
            face_box = detector.detect(frame)
            if face_box is None:
                print(f"  帧{frame_count}: 未检测到人脸")
                frame_count += 1
                continue

            # 提取ROI
            roi = extract_roi(frame, face_box, CONFIG)
            if roi is None:
                print(f"  帧{frame_count}: ROI提取失败")
                frame_count += 1
                continue

            signal_buffer.append(roi)
            frame_count += 1

            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                print(f"  已采集 {frame_count} 帧 ({elapsed:.1f}秒)")

        print(f"\n✓ 信号采集完成: {frame_count}帧")

        # 提取BVP信号
        print("\n提取BVP信号...")
        roi_frames = signal_buffer.get_frames()
        bvp = extract_bvp(
            roi_frames,
            CONFIG["camera_fps"],
            method=CONFIG["rppg_method"],
            is_nir=CONFIG["is_nir_camera"]
        )

        print(f"✓ BVP信号提取成功")
        print(f"  - 信号长度: {len(bvp)}")
        print(f"  - 信号范围: [{np.min(bvp):.3f}, {np.max(bvp):.3f}]")
        print(f"  - 信号标准差: {np.std(bvp):.3f}")

        # 估计心率
        print("\n估计心率...")
        hr = estimate_hr(bvp, CONFIG["camera_fps"])
        print(f"✓ 心率估计: {hr:.1f} BPM")

        if 40 <= hr <= 120:
            print(f"  心率在合理范围内 (40-120 BPM)")
        else:
            print(f"  ⚠ 心率超出正常范围，可能需要调整")

        camera.release()
        print("\n✓ NIR-rPPG信号提取测试通过\n")
        return True

    except Exception as e:
        print(f"✗ NIR-rPPG测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_hrv_risk():
    """测试3：HRV风险评估"""
    print("=" * 60)
    print("测试3：HRV风险评估（NIR模式）")
    print("=" * 60)

    try:
        calculator = NIRHRVRiskCalculator(CONFIG)
        print(f"✓ HRV风险计算器初始化成功")
        print(f"  - 模式: {CONFIG.get('nir_hrv_mode', 'simplified')}")
        print(f"  - NIR相机: {CONFIG.get('is_nir_camera', False)}")

        # 测试不同的HRV特征
        test_cases = [
            {
                "name": "正常状态",
                "features": {
                    "rmssd": 35.0,
                    "sdnn": 60.0,
                    "lf_hf": 1.5,
                    "mean_hr": 70.0,
                    "ibi_count": 50,
                    "valid": True
                }
            },
            {
                "name": "轻度疲劳",
                "features": {
                    "rmssd": 22.0,
                    "sdnn": 40.0,
                    "lf_hf": 2.5,
                    "mean_hr": 65.0,
                    "ibi_count": 50,
                    "valid": True
                }
            },
            {
                "name": "重度疲劳",
                "features": {
                    "rmssd": 12.0,
                    "sdnn": 20.0,
                    "lf_hf": 4.5,
                    "mean_hr": 55.0,
                    "ibi_count": 50,
                    "valid": True
                }
            }
        ]

        print("\n测试不同疲劳状态的风险评分：")
        for case in test_cases:
            risk = calculator.calculate_risk(case["features"])
            print(f"\n  {case['name']}:")
            print(f"    - RMSSD: {case['features']['rmssd']:.1f} ms")
            print(f"    - SDNN: {case['features']['sdnn']:.1f} ms")
            print(f"    - 心率: {case['features']['mean_hr']:.1f} BPM")
            print(f"    → 风险评分: {risk:.3f}")

        print("\n✓ HRV风险评估测试通过\n")
        return True

    except Exception as e:
        print(f"✗ HRV风险评估测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("NIR-rPPG 系统测试")
    print("=" * 60)
    print(f"配置信息：")
    print(f"  - 相机: {CONFIG['camera_width']}x{CONFIG['camera_height']} @ {CONFIG['camera_fps']} FPS")
    print(f"  - NIR模式: {CONFIG['is_nir_camera']}")
    print(f"  - rPPG方法: {CONFIG['rppg_method']}")
    print(f"  - HRV模式: {CONFIG.get('nir_hrv_mode', 'simplified')}")
    print("=" * 60 + "\n")

    results = []

    # 测试1：相机采集
    results.append(("相机采集", test_camera()))

    # 测试2：NIR-rPPG信号提取
    if results[-1][1]:  # 如果相机测试通过
        results.append(("NIR-rPPG信号提取", test_nir_rppg()))
    else:
        print("⊗ 跳过NIR-rPPG测试（相机测试未通过）\n")
        results.append(("NIR-rPPG信号提取", False))

    # 测试3：HRV风险评估
    results.append(("HRV风险评估", test_hrv_risk()))

    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {name}")

    all_passed = all(r[1] for r in results)
    print("=" * 60)
    if all_passed:
        print("✓ 所有测试通过！系统可以正常使用。")
    else:
        print("✗ 部分测试失败，请检查配置和硬件连接。")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
