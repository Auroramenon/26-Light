"""疲劳驾驶光电预警系统 — 主程序入口stm

用法:
    python main.py
    python main.py --camera 1 --serial COM5 --method POS --no-serial
    python main.py --record --session test_001  # 启用数据记录
"""

import argparse
import time
import cv2
import numpy as np

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector
from face.tracker import FaceTracker
from face.roi import extract_roi, get_roi_coords, extract_reference_region
from rppg.signal_buffer import SignalBuffer
from rppg.unsupervised import extract_bvp
from rppg.signal_quality import compute_bvp_sqi, hrv_confidence, behavior_confidence
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
    # 用相机实际帧率驱动 rPPG DSP（缓冲长度、FFT→BPM 换算），
    # 避免非 30fps 硬件因沿用标称帧率导致的系统性心率偏差。
    _measured_fps = float(camera.fps) if camera.fps else float(cfg["camera_fps"])
    fps = float(np.clip(_measured_fps, 10.0, 60.0))
    if abs(fps - cfg["camera_fps"]) >= 1.0:
        print(f"[相机] 实测帧率 {fps:.1f} FPS 与标称 {cfg['camera_fps']} 不同，"
              f"以实测值驱动信号处理")

    face_det = FaceDetector(cfg)
    tracker = FaceTracker()
    sig_buf = SignalBuffer(fps, cfg["signal_window_sec"])
    # 参考区滑窗（环境红外共模抑制用），与 sig_buf 逐帧对齐
    ref_buf = (SignalBuffer(fps, cfg["signal_window_sec"])
               if cfg.get("illum_rejection_enabled", False)
               and cfg.get("rppg_method", "") == "NIR_CMR" else None)
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
    _last_ref = None         # 上一帧可用的参考区（无法提取时复用，保持缓冲区对齐）
    bvp_sqi = 0.0            # 最近一次 BVP 信号质量指数
    hrv_conf = 0.0           # HRV 通道置信度（用于自适应融合）
    risks = {}              # 各路风险分（保证 recorder/日志始终有定义）
    last_roi_time = 0.0     # 上次成功入缓冲的时间，用于人脸丢失后的时序断裂重置
    last_eval_time = 0.0    # 融合/分级/串口的统一评估节流时间戳
    _cached_head_pitch = 0.0  # 头姿缓存（仅在新 landmark 到达时用 solvePnP 重算）
    eval_interval = cfg.get("eval_interval_sec", 0.2)      # 统一评估节律（秒），默认 5Hz
    gap_reset_sec = cfg.get("buffer_gap_reset_sec", 1.0)   # 帧序列断裂重置阈值（秒）
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
            _fresh_landmarks = (_mp_frame_count % _mp_interval == 0)

            perclos = eye_det.update(landmarks)
            yawn_rate = yawn_det.update(landmarks)
            # 头姿 solvePnP 开销较大：仅在有新 landmark 时重算，其余帧复用缓存
            if _fresh_landmarks:
                _cached_head_pitch = head_est.update(landmarks, frame.shape)
            head_pitch = _cached_head_pitch

            # --- ROI + rPPG（仅负责更新 bvp/hr/hrv/sqi，不做分级下发） ---
            roi_coords = None
            if current_box is not None:
                roi = extract_roi(frame, current_box, cfg)
                roi_coords = get_roi_coords(current_box, cfg, frame.shape)

                if roi is not None:
                    # 人脸丢失后重新捕获：若与上次入缓冲间隔过大，说明帧序列时序断裂，
                    # 清空缓冲并复位生理量，避免用不连续帧计算出错误心率/HRV。
                    if last_roi_time > 0.0 and (now - last_roi_time) > gap_reset_sec:
                        sig_buf.clear()
                        if ref_buf is not None:
                            ref_buf.clear()
                        ibi_acc.reset()          # 清空断裂前的心跳间期，避免 HRV 失真
                        hrv_features = {}
                        hrv_reason = "not_ready"
                        _hr_prev = None
                        hr = 0.0
                        bvp = None
                        bvp_sqi = 0.0
                        hrv_conf = 0.0
                        last_rppg_time = 0.0
                    last_roi_time = now

                    sig_buf.append(roi)

                    # 参考区与 ROI 逐帧对齐入缓冲，供环境红外共模抑制使用
                    if ref_buf is not None:
                        ref = extract_reference_region(frame, current_box, cfg)
                        if ref is not None:
                            _last_ref = ref
                        ref_buf.append(_last_ref if _last_ref is not None
                                       else np.zeros_like(roi))

                    rppg_interval = cfg.get("rppg_update_interval_sec", 1.0)
                    if sig_buf.is_ready() and (now - last_rppg_time) >= rppg_interval:
                        last_rppg_time = now
                        try:
                            short_frames = sig_buf.get_frames()
                            ref_frames = ref_buf.get_frames() if ref_buf is not None else None
                            if use_neural and neural_rppg is not None:
                                bvp = neural_rppg.predict(short_frames)
                            else:
                                bvp = extract_bvp(short_frames, fps, cfg["rppg_method"],
                                                  cfg.get("is_nir_camera", False),
                                                  ref_frames=ref_frames)

                            # 信号质量指数（SQI）→ HRV 通道置信度
                            bvp_sqi = compute_bvp_sqi(
                                bvp, fps,
                                cfg.get("sqi_band_low", 0.7), cfg.get("sqi_band_high", 2.5))

                            hr_raw = estimate_hr(bvp, fps, cfg["bandpass_low"], cfg["bandpass_high"])
                            _hr_alpha = cfg.get("hr_ema_alpha", 0.3)
                            if hr_raw > 0:
                                if _hr_prev is None:
                                    hr = hr_raw
                                else:
                                    hr = _hr_alpha * hr_raw + (1.0 - _hr_alpha) * _hr_prev
                                _hr_prev = hr

                            # 从短窗口 BVP 提取 IBI 并累积到 60s 滑窗
                            ibi_acc.feed_bvp(bvp, fps)
                            hrv_features = ibi_acc.compute()
                            hrv_reason = hrv_features.get("reason", "ok")

                            hrv_conf = hrv_confidence(
                                bvp_sqi, hrv_features.get("ibi_count", 0),
                                cfg.get("hrv_min_ibi_count", 20))
                        except Exception as e:
                            print(f"[rPPG] 处理异常: {e}")

            # --- 统一评估：融合 + 分级 + 串口下发（固定节律，独立于 rPPG 计算频率） ---
            # 无论 rPPG 是否就绪都以恒定节律评估，保证 EMA 平滑时间常数稳定、串口流量可控。
            if now - last_eval_time >= eval_interval:
                last_eval_time = now
                beh_conf = behavior_confidence(landmarks is not None)
                confidences = {
                    "hrv": hrv_conf if hrv_features.get("valid", False) else 0.0,
                    "perclos": beh_conf, "yawn": beh_conf, "head": beh_conf,
                }
                fatigue_score, risks = fuser.fuse(
                    hrv_features, perclos, yawn_rate, head_pitch,
                    confidences=confidences)
                level = classifier.update(fatigue_score, risks)
                serial_out.send(level, hr, now=now)

            if now - last_status_log >= 5.0:
                serial_status = serial_out.status()
                hrv_status = 'OK' if hrv_features.get('valid', False) else 'PENDING'
                hrv_detail = ""
                if hrv_features.get('valid', False):
                    hrv_detail = f" RMSSD={hrv_features.get('rmssd', 0):.1f} SDNN={hrv_features.get('sdnn', 0):.1f} IBI={hrv_features.get('ibi_count', 0)}"
                _w = getattr(fuser, "_last_weights", None)
                _w_detail = (f" w[hrv/pc/yw/hd]={_w['hrv']:.2f}/{_w['perclos']:.2f}/"
                             f"{_w['yawn']:.2f}/{_w['head']:.2f}") if _w else ""
                print(
                    f"[状态] level={level} score={fatigue_score:.2f} hr={hr:.0f} "
                    f"SQI={bvp_sqi:.2f} hrv_conf={hrv_conf:.2f}{_w_detail} "
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
        print("[系统] 已退出")


if __name__ == "__main__":
    main()
