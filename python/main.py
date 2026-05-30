"""疲劳驾驶光电预警系统 — 主程序入口stm

用法:
    python main.py
    python main.py --camera 1 --serial COM5 --method POS --no-serial
    python main.py --record --session test_001  # 启用数据记录
"""

import argparse
import signal
import time
import cv2
import numpy as np

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
from data_logger.recorder import DataRecorder
from display.oled_screen import OLEDScreen


def parse_args():
    p = argparse.ArgumentParser(description="疲劳驾驶光电预警系统")
    p.add_argument("--camera", type=int, default=None, help="相机索引")
    p.add_argument("--serial", type=str, default=None, help="串口号 (如 COM3)")
    p.add_argument("--method", type=str, default=None, choices=["CHROM", "POS"])
    p.add_argument("--no-serial", action="store_true", help="禁用串口")
    p.add_argument("--no-gui", action="store_true", help="禁用GUI")
    p.add_argument("--face-backend", type=str, default=None, choices=["HC", "Y5F"])
    p.add_argument("--record", action="store_true", help="启用数据记录")
    p.add_argument("--session", type=str, default=None, help="测试会话名称")
    p.add_argument("--output-dir", type=str, default="test_data", help="数据输出目录")
    p.add_argument("--sample-interval", type=float, default=1.0, help="数据采样间隔（秒），默认1.0")
    return p.parse_args()


def main():
    args = parse_args()

    # systemd stop 发送 SIGTERM，默认不触发 finally 收尾（不清屏、不释放设备）。
    # 转成 KeyboardInterrupt，复用下方 try/finally 的优雅退出逻辑。
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

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
    # NIR模式降低置信度阈值：MediaPipe在近红外图像上特征响应较弱
    _mp_conf = 0.3 if cfg.get("is_nir_camera", False) else 0.5
    mp_face = get_face_mesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=_mp_conf, min_tracking_confidence=_mp_conf)

    # NIR图像预处理：CLAHE自适应直方图均衡，提升MediaPipe在近红外下的检测率
    _clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)) if cfg.get("is_nir_camera", False) else None

    eye_det = EyeDetector(cfg)
    yawn_det = YawnDetector(cfg)
    head_est = HeadPoseEstimator(cfg)

    serial_out = SerialSender(cfg)
    display = Display(cfg)

    oled = None
    if cfg.get("oled_enabled", False):
        try:
            oled = OLEDScreen(
                chip=cfg["oled_gpio_chip"],
                dc_line=cfg["oled_dc_line"],
                rst_line=cfg["oled_rst_line"],
                port=cfg["oled_spi_port"],
                device=cfg["oled_spi_device"],
            )
            oled.show_boot_screen()
        except Exception as e:
            print(f"[WARN] 小屏幕初始化失败，跳过: {e}")
            oled = None
    last_oled_update = 0.0

    # 有状态的融合器和分类器
    fuser = FeatureFuser(cfg)
    classifier = FatigueClassifier(cfg)

    # 数据记录器（可选）
    recorder = None
    if args.record:
        recorder = DataRecorder(
            output_dir=args.output_dir,
            session_name=args.session,
            sample_interval=args.sample_interval
        )
        recorder.set_config(cfg)
        print(f"[系统] 数据记录已启用: {recorder.session_name}")

    # 状态变量
    last_detect_time = 0.0
    last_rppg_time = 0.0     # BVP/HR 节流时间戳
    current_box = None
    hr = 0.0
    _hr_prev = None          # HR EMA 平滑状态
    level = 0
    fatigue_score = 0.0
    perclos = 0.0
    yawn_rate = 0
    head_pitch = 0.0
    bvp = None
    hrv_features = {}
    hrv_reason = "not_ready"
    last_status_log = 0.0
    # MediaPipe 降频：ARM 上每 N 帧推理一次，中间帧复用上次 landmark
    _mp_interval = cfg.get("mediapipe_interval", 3)  # 默认 10Hz@30fps
    _mp_frame_count = 0
    _cached_landmarks = None

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

            # --- 行为特征（每 _mp_interval 帧推理一次，ARM 降负载） ---
            _mp_frame_count += 1
            if _mp_frame_count % _mp_interval == 0:
                if _clahe is not None:
                    _gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    _eq = _clahe.apply(_gray)
                    rgb_frame = np.ascontiguousarray(np.stack([_eq, _eq, _eq], axis=-1))
                else:
                    rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
                mp_result = mp_face.process(rgb_frame)
                _cached_landmarks = (mp_result.multi_face_landmarks[0].landmark
                                     if mp_result.multi_face_landmarks else None)
            landmarks = _cached_landmarks

            perclos = eye_det.update(landmarks)
            yawn_rate = yawn_det.update(landmarks)
            head_pitch = head_est.update(landmarks, frame.shape)

            # --- ROI + rPPG ---
            roi_coords = None
            sent_to_strip = False
            if current_box is not None:
                roi = extract_roi(frame, current_box, cfg)
                roi_coords = get_roi_coords(current_box, cfg, frame.shape)

                if roi is not None:
                    sig_buf.append(roi)

                    rppg_interval = cfg.get("rppg_update_interval_sec", 1.0)
                    if sig_buf.is_ready() and (now - last_rppg_time) >= rppg_interval:
                        last_rppg_time = now
                        try:
                            short_frames = sig_buf.get_frames()
                            if use_neural and neural_rppg is not None:
                                bvp = neural_rppg.predict(short_frames)
                            else:
                                bvp = extract_bvp(short_frames, fps, cfg["rppg_method"], cfg.get("is_nir_camera", False))

                            hr_fft = estimate_hr(bvp, fps, cfg["bandpass_low"], cfg["bandpass_high"])

                            # 从短窗口 BVP 提取 IBI 并累积到 60s 滑窗
                            ibi_acc.feed_bvp(bvp, fps)
                            hrv_features = ibi_acc.compute()

                            # 心率融合：IBI峰间隔法比FFT更准，优先采用
                            # 要求至少8个IBI且与FFT结果偏差 <25 BPM 才信任IBI心率
                            ibi_hr = hrv_features.get("mean_hr", 0.0)
                            ibi_valid = (
                                hrv_features.get("valid", False)
                                and hrv_features.get("ibi_count", 0) >= 8
                                and 40.0 < ibi_hr < 180.0
                                and (hr_fft <= 0 or abs(ibi_hr - hr_fft) < 25.0)
                            )
                            if ibi_valid:
                                hr_candidate = ibi_hr
                            elif hr_fft > 0:
                                hr_candidate = hr_fft
                            else:
                                hr_candidate = 0.0

                            _hr_alpha = cfg.get("hr_ema_alpha", 0.3)
                            if hr_candidate > 0:
                                if _hr_prev is None:
                                    hr = hr_candidate
                                else:
                                    hr = _hr_alpha * hr_candidate + (1.0 - _hr_alpha) * _hr_prev
                                _hr_prev = hr
                            hrv_reason = hrv_features.get("reason", "ok")

                            fatigue_score, risks = fuser.fuse(
                                hrv_features, perclos, yawn_rate, head_pitch)
                            level = classifier.update(fatigue_score, risks)

                            serial_out.send(level, hr, now=now)
                            sent_to_strip = True
                        except Exception as e:
                            print(f"[rPPG] 处理异常: {e}")

            if not sent_to_strip:
                # 当 rPPG / HRV 尚未就绪时，仍然基于摄像头行为特征进行等级评估并同步灯带状态
                fatigue_score, risks = fuser.fuse(
                    hrv_features, perclos, yawn_rate, head_pitch)
                level = classifier.update(fatigue_score, risks)
                serial_out.send(level, hr, now=now)

            if now - last_status_log >= 5.0:
                serial_status = serial_out.status()
                hrv_status = 'OK' if hrv_features.get('valid', False) else 'PENDING'
                hrv_detail = ""
                if hrv_features.get('valid', False):
                    hrv_detail = f" RMSSD={hrv_features.get('rmssd', 0):.1f} SDNN={hrv_features.get('sdnn', 0):.1f} IBI={hrv_features.get('ibi_count', 0)}"
                print(
                    f"[状态] level={level} score={fatigue_score:.2f} hr={hr:.0f} "
                    f"HRV={hrv_status}({hrv_reason}){hrv_detail} "
                    f"串口={serial_status['state']} fail={serial_status['failures']} "
                    f"drop={serial_status['rate_limited_drops']}"
                )
                if recorder:
                    print(f"[记录] {recorder.get_summary()}")
                last_status_log = now

            # --- 数据记录 ---
            if recorder:
                recorder.record({
                    "hr": hr,
                    "hrv_features": hrv_features,
                    "perclos": perclos,
                    "yawn_rate": yawn_rate,
                    "head_pitch": head_pitch,
                    "fatigue_score": fatigue_score,
                    "fatigue_level": level,
                    "risks": risks if 'risks' in locals() else {}
                })

            # --- 小屏幕刷新 ---
            if oled is not None and (now - last_oled_update) >= cfg["oled_update_interval"]:
                try:
                    oled.update(level, hr, fatigue_score, perclos, yawn_rate)
                    last_oled_update = now
                except Exception as e:
                    print(f"[WARN] 小屏幕刷新失败: {e}")

            # --- GUI ---
            display.render(
                frame, box=current_box, roi_coords=roi_coords,
                hr=hr, level=level, fatigue_score=fatigue_score,
                perclos=perclos, yawn_rate=yawn_rate, bvp=bvp,
                hrv_features=hrv_features)

            if display.check_quit():
                break

    except KeyboardInterrupt:
        print("\n[系统] 用户中断")
    finally:
        camera.release()
        serial_out.close()
        display.close()
        mp_face.close()
        if recorder:
            recorder.close()
        if oled is not None:
            oled.clear()
        print("[系统] 已退出")


if __name__ == "__main__":
    main()
