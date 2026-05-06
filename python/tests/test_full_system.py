"""完整系统调试脚本 - 实时显示所有指标"""

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
from rppg.hrv_analyzer import IBIAccumulator
from behavior.eye_detector import EyeDetector
from behavior.yawn_detector import YawnDetector
from fusion.feature_fusion import FeatureFuser

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    HAS_MEDIAPIPE = True
except:
    HAS_MEDIAPIPE = False
    print("⚠ MediaPipe未安装，行为检测将被禁用")


def test_full_system():
    """完整系统调试"""
    print("=" * 60)
    print("完整系统调试")
    print("=" * 60)

    # 初始化
    print("\n[1] 初始化模块...")
    camera = Camera(CONFIG)
    detector = FaceDetector(CONFIG)
    signal_buffer = SignalBuffer(CONFIG["camera_fps"], CONFIG["signal_window_sec"])
    hrv_accumulator = IBIAccumulator(CONFIG["hrv_window_sec"], CONFIG["hrv_update_interval_sec"])
    fuser = FeatureFuser(CONFIG)

    if HAS_MEDIAPIPE:
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        eye_detector = EyeDetector(CONFIG)
        yawn_detector = YawnDetector(CONFIG)
    else:
        face_mesh = None

    print("✓ 初始化完成")

    # 状态变量
    current_hr = 0.0
    current_hrv = {"valid": False}
    current_perclos = 0.0
    current_yawn_rate = 0.0
    current_head_pitch = 0.0
    fatigue_score = 0.0
    fatigue_level = 0

    print("\n[2] 开始实时监测（按 'q' 退出）...")
    print("提示：")
    print("  - 左上角：实时指标")
    print("  - 右上角：疲劳评分和等级")
    print("  - 绿色框：人脸")
    print("  - 蓝色框：ROI\n")

    frame_count = 0
    last_rppg_update = time.time()

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        frame_count += 1
        display_frame = frame.copy()

        # 人脸检测
        face_box = detector.detect(frame)

        if face_box is not None:
            x1, y1, x2, y2 = face_box

            # 绘制人脸框
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 提取ROI
            roi = extract_roi(frame, face_box, CONFIG)
            if roi is not None:
                # 绘制ROI框
                face_w = x2 - x1
                face_h = y2 - y1
                roi_x1 = int(x1 + face_w * CONFIG["roi_x_start"])
                roi_y1 = int(y1 + face_h * CONFIG["roi_y_start"])
                roi_x2 = int(x1 + face_w * CONFIG["roi_x_end"])
                roi_y2 = int(y1 + face_h * CONFIG["roi_y_end"])
                cv2.rectangle(display_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 0, 0), 2)

                # 添加到信号缓冲区
                signal_buffer.append(roi)

                # rPPG更新（每2秒）
                if signal_buffer.is_ready() and time.time() - last_rppg_update > 2.0:
                    roi_frames = signal_buffer.get_frames()
                    bvp = extract_bvp(roi_frames, CONFIG["camera_fps"],
                                     method=CONFIG["rppg_method"],
                                     is_nir=CONFIG["is_nir_camera"])
                    current_hr = estimate_hr(bvp, CONFIG["camera_fps"])
                    hrv_accumulator.feed_bvp(bvp, CONFIG["camera_fps"])
                    current_hrv = hrv_accumulator.compute()
                    last_rppg_update = time.time()

            # 行为检测（如果有MediaPipe）
            if HAS_MEDIAPIPE and face_mesh:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)

                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    current_perclos = eye_detector.update(landmarks)
                    current_yawn_rate = yawn_detector.update(landmarks)

        # 多模态融合
        if current_hrv.get("valid", False):
            fatigue_score, risks = fuser.fuse(
                current_hrv,
                current_perclos,
                current_yawn_rate,
                current_head_pitch
            )

            # 疲劳等级判定
            if fatigue_score >= CONFIG["upgrade_thresholds"][2]:
                fatigue_level = 3
            elif fatigue_score >= CONFIG["upgrade_thresholds"][1]:
                fatigue_level = 2
            elif fatigue_score >= CONFIG["upgrade_thresholds"][0]:
                fatigue_level = 1
            else:
                fatigue_level = 0

        # 显示信息
        y_offset = 30
        line_height = 30

        # 左侧：实时指标
        cv2.putText(display_frame, f"HR: {current_hr:.1f} BPM",
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += line_height

        if current_hrv.get("valid", False):
            cv2.putText(display_frame, f"RMSSD: {current_hrv['rmssd']:.1f} ms",
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += line_height

        cv2.putText(display_frame, f"PERCLOS: {current_perclos:.2f}",
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += line_height

        cv2.putText(display_frame, f"Yawn: {current_yawn_rate:.1f}/min",
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 右侧：疲劳评分
        cv2.putText(display_frame, f"Score: {fatigue_score:.3f}",
                   (display_frame.shape[1] - 250, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # 疲劳等级（带颜色）
        level_colors = [(0, 255, 0), (0, 255, 255), (0, 165, 255), (0, 0, 255)]
        level_names = ["Normal", "Mild", "Moderate", "Severe"]
        cv2.putText(display_frame, f"Level: {fatigue_level} ({level_names[fatigue_level]})",
                   (display_frame.shape[1] - 250, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, level_colors[fatigue_level], 2)

        # 信号缓冲进度
        if not signal_buffer.is_ready():
            progress = len(signal_buffer) / signal_buffer.max_len * 100
            cv2.putText(display_frame, f"Buffering: {progress:.0f}%",
                       (display_frame.shape[1] - 250, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow('Full System Debug', display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)
    print(f"总帧数: {frame_count}")
    print(f"最终心率: {current_hr:.1f} BPM")
    print(f"最终疲劳评分: {fatigue_score:.3f}")
    print(f"最终疲劳等级: {fatigue_level}")


if __name__ == "__main__":
    test_full_system()
