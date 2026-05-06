"""仅测试NIR-rPPG功能（不需要mediapipe）"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.roi import extract_roi
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.hr_estimator import estimate_hr

def main():
    print("=" * 60)
    print("NIR-rPPG 心率检测测试（无需mediapipe）")
    print("=" * 60)

    camera = Camera(CONFIG)
    detector = FaceDetector(CONFIG)
    signal_buffer = SignalBuffer(CONFIG["camera_fps"], CONFIG["signal_window_sec"])

    print(f"\n采集信号中...")
    print(f"需要 {CONFIG['signal_window_sec']} 秒")
    print("提示：保持面部静止，正对相机\n")

    frame_count = 0
    start_time = time.time()

    while not signal_buffer.is_ready():
        ret, frame = camera.read()
        if not ret:
            print("读取帧失败")
            continue

        face_box = detector.detect(frame)
        if face_box is None:
            print(f"  帧{frame_count}: 未检测到人脸")
            frame_count += 1
            continue

        roi = extract_roi(frame, face_box, CONFIG)
        if roi is None:
            print(f"  帧{frame_count}: ROI提取失败")
            frame_count += 1
            continue

        signal_buffer.append(roi)
        frame_count += 1

        if frame_count % 30 == 0:
            progress = len(signal_buffer) / signal_buffer.max_len * 100
            elapsed = time.time() - start_time
            print(f"  进度: {progress:.0f}% ({elapsed:.1f}秒)")

    print(f"\n[OK] 信号采集完成: {frame_count}帧")

    print(f"\n提取BVP信号...")
    roi_frames = signal_buffer.get_frames()
    bvp = extract_bvp(roi_frames, CONFIG["camera_fps"],
                     method=CONFIG["rppg_method"],
                     is_nir=CONFIG["is_nir_camera"])

    print(f"[OK] BVP信号提取成功")
    print(f"  - 信号长度: {len(bvp)}")
    print(f"  - 信号范围: [{bvp.min():.3f}, {bvp.max():.3f}]")

    print(f"\n估计心率...")
    hr = estimate_hr(bvp, CONFIG["camera_fps"])

    print(f"\n" + "=" * 60)
    print(f"心率: {hr:.1f} BPM")
    print(f"=" * 60)

    if 40 <= hr <= 120:
        print("[OK] 心率在合理范围内 (40-120 BPM)")
    else:
        print("[!] 心率超出正常范围，可能需要调整")

    camera.release()
    print("\n测试完成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
