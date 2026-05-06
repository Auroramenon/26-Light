"""心率准确度调试脚本 - 对比真实心率"""

import cv2
import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.roi import extract_roi
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.hr_estimator import estimate_hr


def test_hr_accuracy():
    """测试心率准确度（需要手动输入真实心率）"""
    print("=" * 60)
    print("心率准确度调试")
    print("=" * 60)

    # 获取真实心率
    print("\n请先测量真实心率（使用指夹式血氧仪或手动测量）")
    real_hr = float(input("输入真实心率 (BPM): "))

    # 初始化
    camera = Camera(CONFIG)
    detector = FaceDetector(CONFIG)

    # 多次测量
    num_tests = 3
    estimated_hrs = []

    for test_num in range(num_tests):
        print(f"\n[测试 {test_num+1}/{num_tests}]")
        print("保持静止，开始采集...")

        signal_buffer = SignalBuffer(CONFIG["camera_fps"], CONFIG["signal_window_sec"])
        frame_count = 0

        while not signal_buffer.is_ready():
            ret, frame = camera.read()
            if not ret:
                continue

            face_box = detector.detect(frame)
            if face_box is None:
                continue

            roi = extract_roi(frame, face_box, CONFIG)
            if roi is None:
                continue

            signal_buffer.append(roi)
            frame_count += 1

            if frame_count % 30 == 0:
                progress = len(signal_buffer) / signal_buffer.max_len * 100
                print(f"  进度: {progress:.1f}%")

        # 提取心率
        roi_frames = signal_buffer.get_frames()
        bvp = extract_bvp(roi_frames, CONFIG["camera_fps"],
                         method=CONFIG["rppg_method"],
                         is_nir=CONFIG["is_nir_camera"])
        hr = estimate_hr(bvp, CONFIG["camera_fps"])

        estimated_hrs.append(hr)
        error = abs(hr - real_hr)
        print(f"  估计心率: {hr:.1f} BPM")
        print(f"  误差: {error:.1f} BPM")

        if test_num < num_tests - 1:
            print("  等待5秒后进行下一次测试...")
            time.sleep(5)

    camera.release()

    # 统计
    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"真实心率: {real_hr:.1f} BPM")
    print(f"估计心率: {np.mean(estimated_hrs):.1f} ± {np.std(estimated_hrs):.1f} BPM")
    print(f"平均误差: {np.mean([abs(hr - real_hr) for hr in estimated_hrs]):.1f} BPM")
    print(f"最大误差: {max([abs(hr - real_hr) for hr in estimated_hrs]):.1f} BPM")

    # 评估
    avg_error = np.mean([abs(hr - real_hr) for hr in estimated_hrs])
    if avg_error < 5:
        print("\n✓ 准确度优秀 (误差<5 BPM)")
    elif avg_error < 8:
        print("\n✓ 准确度良好 (误差<8 BPM)")
    elif avg_error < 12:
        print("\n⚠ 准确度一般 (误差<12 BPM)")
        print("建议：")
        print("  1. 增加信号窗口长度")
        print("  2. 使用 NIR_ROBUST 算法")
        print("  3. 确保面部静止")
    else:
        print("\n❌ 准确度较差 (误差>12 BPM)")
        print("可能的原因：")
        print("  1. 补光不足")
        print("  2. 运动伪影严重")
        print("  3. ROI区域选择不当")
        print("  4. 相机质量问题")


if __name__ == "__main__":
    test_hr_accuracy()
