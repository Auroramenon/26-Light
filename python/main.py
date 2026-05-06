"""疲劳驾驶光电预警系统 — 主程序入口

用法:
    python main.py
    python main.py --camera 1 --serial COM5 --method POS --no-serial
"""

import argparse
import time

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.tracker import FaceTracker
from face.roi import extract_roi, get_roi_coords
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.neural import NeuralRPPG
from rppg.hr_estimator import estimate_hr
from rppg.hrv_analyzer import IBIAccumulator
from behavior.eye_detector import EyeDetector
from behavior.yawn_detector import YawnDetector
from behavior.head_pose import HeadPoseEstimator
from behavior.mediapipe_compat import get_face_mesh
from fusion.feature_fusion import FeatureFuser
from fusion.fatigue_classifier import FatigueClassifier, LEVEL_NAMES
from comm.serial_sender import SerialSender
from gui.display import Display


def parse_args():
    p = argparse.ArgumentParser(description="疲劳驾驶光电预警系统")
    p.add_argument("--camera", type=int, default=None, help="相机索引")
    p.add_argument("--serial", type=str, default=None, help="串口号 (如 COM3)")
    p.add_argument("--method", type=str, default=None, choices=["CHROM", "POS"])
    p.add_argument("--no-serial", action="store_true", help="禁用串口")
    p.add_argument("--no-gui", action="store_true", help="禁用GUI")
    p.add_argument("--face-backend", type=str, default=None, choices=["HC", "Y5F"])
    return p.parse_args()


def main():
    args = parse_args()

    # 合并命令行参数到配置
    cfg = dict(CONFIG)
    if args.camera is not None:
        cfg["camera_index"] = args.camera
    if args.serial is not None:
        cfg["serial_port"] = args.serial
    if args.method is not None:
        cfg["rppg_method"] = args.method
    if args.no_serial:
        cfg["serial_enabled"] = False
    if args.no_gui:
        cfg["show_gui"] = False
    if args.face_backend is not None:
        cfg["face_det_backend"] = args.face_backend

    # 初始化各模块
    print("[系统] 正在初始化...")
    camera = Camera(cfg)
    fps = cfg["camera_fps"]

    face_det = FaceDetector(cfg)
    tracker = FaceTracker()
    sig_buf = SignalBuffer(fps, cfg["signal_window_sec"])
    ibi_acc = IBIAccumulator(
        window_sec=cfg["hrv_window_sec"],
        update_interval=cfg.get("hrv_update_interval_sec", 1.0))

    # rPPG分支：无监督/神经网络二选一
    neural_rppg = None
    use_neural = cfg.get("use_neural", False)
    bvp_backend = cfg["rppg_method"]
    if use_neural:
        try:
            neural_rppg = NeuralRPPG(cfg)
            bvp_backend = f"NEURAL:{cfg['neural_model']}"
        except Exception as e:
            print(f"[rPPG] 神经网络分支初始化失败，回退到{cfg['rppg_method']}: {e}")
            use_neural = False

    # MediaPipe Face Mesh（行为检测共用）
    mp_face = get_face_mesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5)

    eye_det = EyeDetector(cfg)
    yawn_det = YawnDetector(cfg)
    head_est = HeadPoseEstimator(cfg)

    serial_out = SerialSender(cfg)
    display = Display(cfg)

    # 有状态的融合器和分类器
    fuser = FeatureFuser(cfg)
    classifier = FatigueClassifier(cfg)

    # 状态变量
    last_detect_time = 0.0
    current_box = None
    hr = 0.0
    level = 0
    fatigue_score = 0.0
    perclos = 0.0
    yawn_rate = 0
    head_pitch = 0.0
    bvp = None
    hrv_features = {}
    hrv_reason = "not_ready"
    last_status_log = 0.0

    print("[系统] 初始化完成，开始运行 (按 q 退出)")
    print(f"[配置] 相机={cfg['camera_index']} 后端={camera.backend_name} 方法={cfg['rppg_method']} "
          f"人脸={cfg['face_det_backend']} 串口={cfg['serial_port'] if cfg['serial_enabled'] else '禁用'}")
    print(f"[配置] BVP后端={bvp_backend} HRV滑窗={cfg['hrv_window_sec']}s(IBI累积)")

    # ===== 主循环 =====
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("[系统] 相机读取失败")
                break

            now = time.time()
            serial_out.tick(now)

            # --- 人脸检测/跟踪 ---
            if now - last_detect_time >= cfg["face_rescan_interval"] or current_box is None:
                box = face_det.detect(frame)
                if box is not None:
                    current_box = box
                    tracker.init(frame, box)
                last_detect_time = now
            else:
                tracked = tracker.update(frame)
                if tracked is not None:
                    current_box = tracked

            # --- 行为特征（每帧都跑 MediaPipe） ---
            rgb_frame = frame[:, :, ::-1]
            mp_result = mp_face.process(rgb_frame)
            landmarks = None
            if mp_result.multi_face_landmarks:
                landmarks = mp_result.multi_face_landmarks[0].landmark

            perclos = eye_det.update(landmarks)
            yawn_rate = yawn_det.update(landmarks)
            head_pitch = head_est.update(landmarks, frame.shape)

            # --- ROI + rPPG ---
            roi_coords = None
            if current_box is not None:
                roi = extract_roi(frame, current_box, cfg)
                roi_coords = get_roi_coords(current_box, cfg, frame.shape)

                if roi is not None:
                    sig_buf.append(roi)

                    if sig_buf.is_ready():
                        try:
                            short_frames = sig_buf.get_frames()
                            if use_neural and neural_rppg is not None:
                                bvp = neural_rppg.predict(short_frames)
                            else:
                                bvp = extract_bvp(short_frames, fps, cfg["rppg_method"], cfg.get("is_nir_camera", False))

                            hr = estimate_hr(bvp, fps, cfg["bandpass_low"], cfg["bandpass_high"])

                            # 从短窗口 BVP 提取 IBI 并累积到 60s 滑窗
                            ibi_acc.feed_bvp(bvp, fps)
                            hrv_features = ibi_acc.compute()
                            hrv_reason = hrv_features.get("reason", "ok")

                            fatigue_score, risks = fuser.fuse(
                                hrv_features, perclos, yawn_rate, head_pitch)
                            level = classifier.update(fatigue_score, risks)

                            serial_out.send(level, hr, now=now)
                        except Exception as e:
                            print(f"[rPPG] 处理异常: {e}")

            if now - last_status_log >= 5.0:
                serial_status = serial_out.status()
                print(
                    f"[状态] level={level} score={fatigue_score:.2f} hr={hr:.0f} "
                    f"HRV={'OK' if hrv_features.get('valid', False) else 'PENDING'}({hrv_reason}) "
                    f"串口={serial_status['state']} fail={serial_status['failures']} "
                    f"drop={serial_status['rate_limited_drops']}"
                )
                last_status_log = now

            # --- GUI ---
            display.render(
                frame, box=current_box, roi_coords=roi_coords,
                hr=hr, level=level, fatigue_score=fatigue_score,
                perclos=perclos, yawn_rate=yawn_rate, bvp=bvp)

            if display.check_quit():
                break

    except KeyboardInterrupt:
        print("\n[系统] 用户中断")
    finally:
        camera.release()
        serial_out.close()
        display.close()
        mp_face.close()
        print("[系统] 已退出")


if __name__ == "__main__":
    main()
