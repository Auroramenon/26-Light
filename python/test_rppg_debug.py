"""NIR-rPPG信号提取调试脚本 - 带可视化"""

import cv2
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.roi import extract_roi
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.hr_estimator import estimate_hr


def test_rppg_signal():
    """测试NIR-rPPG信号提取（带实时可视化）"""
    print("=" * 60)
    print("NIR-rPPG信号提取调试")
    print("=" * 60)

    # 初始化
    print("\n[1] 初始化...")
    camera = Camera(CONFIG)
    detector = FaceDetector(CONFIG)
    signal_buffer = SignalBuffer(CONFIG["camera_fps"], CONFIG["signal_window_sec"])

    print(f"✓ 初始化完成")
    print(f"  - rPPG方法: {CONFIG['rppg_method']}")
    print(f"  - 信号窗口: {CONFIG['signal_window_sec']}秒")
    print(f"  - 需要采集: {int(CONFIG['camera_fps'] * CONFIG['signal_window_sec'])}帧")

    # 采集信号
    print("\n[2] 采集信号...")
    print("提示：保持面部静止，正对相机\n")

    frame_count = 0
    roi_intensities = []  # 记录ROI平均亮度

    while not signal_buffer.is_ready():
        ret, frame = camera.read()
        if not ret:
            print("读取帧失败")
            return

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

        # 记录ROI亮度
        roi_intensity = np.mean(roi)
        roi_intensities.append(roi_intensity)

        signal_buffer.append(roi)
        frame_count += 1

        if frame_count % 30 == 0:
            progress = len(signal_buffer) / signal_buffer.max_len * 100
            print(f"  进度: {progress:.1f}% ({len(signal_buffer)}/{signal_buffer.max_len}帧)")

    print(f"\n✓ 信号采集完成: {frame_count}帧")

    # 分析原始信号
    print("\n[3] 分析原始信号...")
    roi_intensities = np.array(roi_intensities)
    print(f"  - ROI亮度范围: [{roi_intensities.min():.1f}, {roi_intensities.max():.1f}]")
    print(f"  - ROI亮度均值: {roi_intensities.mean():.1f}")
    print(f"  - ROI亮度标准差: {roi_intensities.std():.1f}")

    if roi_intensities.std() < 1.0:
        print("  ⚠ 信号变化太小，可能无法提取心率")
        print("    建议：增强补光或调整相机位置")

    # 提取BVP信号
    print("\n[4] 提取BVP信号...")
    roi_frames = signal_buffer.get_frames()
    bvp = extract_bvp(
        roi_frames,
        CONFIG["camera_fps"],
        method=CONFIG["rppg_method"],
        is_nir=CONFIG["is_nir_camera"]
    )

    print(f"✓ BVP信号提取成功")
    print(f"  - 信号长度: {len(bvp)}")
    print(f"  - 信号范围: [{bvp.min():.3f}, {bvp.max():.3f}]")
    print(f"  - 信号标准差: {bvp.std():.3f}")

    # 估计心率
    print("\n[5] 估计心率...")
    hr = estimate_hr(bvp, CONFIG["camera_fps"])
    print(f"✓ 心率: {hr:.1f} BPM")

    if 40 <= hr <= 120:
        print(f"  ✓ 心率在合理范围内")
    else:
        print(f"  ⚠ 心率超出正常范围 (40-120 BPM)")
        print(f"    可能的原因：")
        print(f"    1. 信号质量不佳")
        print(f"    2. 运动伪影")
        print(f"    3. 补光不足")

    # 可视化
    print("\n[6] 生成可视化...")
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))

    # 子图1：原始ROI亮度
    axes[0].plot(roi_intensities, 'b-', linewidth=0.5)
    axes[0].set_title('Raw ROI Intensity (原始ROI亮度)')
    axes[0].set_xlabel('Frame (帧)')
    axes[0].set_ylabel('Intensity (亮度)')
    axes[0].grid(True, alpha=0.3)

    # 子图2：BVP信号
    time_axis = np.arange(len(bvp)) / CONFIG["camera_fps"]
    axes[1].plot(time_axis, bvp, 'r-', linewidth=1)
    axes[1].set_title(f'BVP Signal (BVP信号) - Method: {CONFIG["rppg_method"]}')
    axes[1].set_xlabel('Time (秒)')
    axes[1].set_ylabel('Amplitude (幅度)')
    axes[1].grid(True, alpha=0.3)

    # 子图3：频谱分析
    from scipy.fft import fft, fftfreq
    N = len(bvp)
    yf = fft(bvp)
    xf = fftfreq(N, 1/CONFIG["camera_fps"])

    # 只显示正频率部分
    positive_freq_idx = xf > 0
    xf_positive = xf[positive_freq_idx]
    yf_positive = np.abs(yf[positive_freq_idx])

    # 转换为BPM
    xf_bpm = xf_positive * 60

    axes[2].plot(xf_bpm, yf_positive, 'g-', linewidth=1)
    axes[2].axvline(hr, color='r', linestyle='--', label=f'HR = {hr:.1f} BPM')
    axes[2].set_title('Frequency Spectrum (频谱)')
    axes[2].set_xlabel('Frequency (BPM)')
    axes[2].set_ylabel('Magnitude (幅度)')
    axes[2].set_xlim([30, 150])  # 只显示30-150 BPM范围
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout()
    plt.savefig('nir_rppg_debug.png', dpi=150)
    print(f"✓ 可视化已保存为 nir_rppg_debug.png")

    plt.show()

    camera.release()

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_rppg_signal()
