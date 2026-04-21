"""全局配置参数"""

import os

# rPPG-Toolbox 路径
RPPG_TOOLBOX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "rPPG-Toolbox"))

CONFIG = {
    # ===== 相机 =====
    "camera_index": 0,              # LRCP S400 USB设备索引（或设备路径字符串）
    "camera_fps": 30,
    "camera_width": 640,
    "camera_height": 480,

    # ===== 人脸检测 =====
    "face_det_backend": "HC",       # "Y5F"(YOLO5Face,需GPU) 或 "HC"(Haar Cascade)
    "face_rescan_interval": 1.0,    # 全量检测间隔（秒），中间帧用KLT跟踪
    "face_enlarge_ratio": 1.5,      # 人脸框放大系数
    "device": "cuda:0",

    # ===== ROI（前额区域，相对于人脸框的比例） =====
    "roi_x_start": 0.30,
    "roi_x_end": 0.70,
    "roi_y_start": 0.10,
    "roi_y_end": 0.25,

    # ===== rPPG信号 =====
    "signal_window_sec": 8,         # 滑动窗口长度（秒）
    "rppg_method": "CHROM",         # "CHROM" 或 "POS"
    "bandpass_low": 0.7,            # Hz (42 BPM)
    "bandpass_high": 4.0,           # Hz (240 BPM)

    # ===== HRV =====
    "hrv_window_sec": 60,           # HRV计算窗口（秒）

    # ===== 行为检测 =====
    "ear_threshold": 0.2,           # Eye Aspect Ratio 闭眼阈值
    "perclos_window_sec": 60,       # PERCLOS统计窗口（秒）
    "yawn_mar_threshold": 0.6,      # Mouth Aspect Ratio 哈欠阈值
    "yawn_min_frames": 10,          # 连续超阈值帧数才算一次哈欠
    "head_pitch_threshold": 15.0,   # 头部俯仰角阈值（度）

    # ===== 风险映射参数（分段线性） =====
    "perclos_low": 0.15,            # PERCLOS 低于此值 Risk=0
    "perclos_high": 0.30,           # PERCLOS 高于此值 Risk=1
    "yawn_rate_low": 0.2,           # 哈欠频率低于此值 Risk=0 (次/分)
    "yawn_rate_high": 1.0,          # 哈欠频率高于此值 Risk=1 (次/分)
    "head_angle_low": 15.0,         # 头姿偏转低于此值 Risk=0 (度)
    "head_angle_high": 35.0,        # 头姿偏转高于此值 Risk=1 (度)

    # ===== 多模态融合权重 =====
    "w_hrv": 0.35,
    "w_perclos": 0.30,
    "w_yawn": 0.20,
    "w_head": 0.15,

    # ===== EMA 时间平滑 =====
    "ema_alpha": 0.3,               # EMA 平滑系数 (0.2~0.4, 越小越平滑)

    # ===== 疲劳分级阈值 =====
    "fatigue_thresholds": [0.3, 0.5, 0.7],           # 基础阈值（兼容旧版）
    "upgrade_thresholds": [0.30, 0.50, 0.70],         # 升级阈值
    "downgrade_thresholds": [0.25, 0.45, 0.65],       # 降级阈值（低于升级，防抖动）
    "hold_seconds": 5,                                 # 持续性约束（秒）
    "level3_multi_evidence": True,                     # Level 3 是否要求多证据

    # Level 3 多证据阈值（可调）
    # 规则：满足其一即可进入 Level 3：
    # 1) PERCLOS 风险 >= level3_min_perclos_risk
    # 2) HRV 风险 >= level3_min_hrv_risk
    # 3) 哈欠风险 >= level3_min_yawn_risk 且 低头风险 >= level3_min_head_risk
    "level3_min_perclos_risk": 1.0,
    "level3_min_hrv_risk": 0.7,
    "level3_min_yawn_risk": 0.5,
    "level3_min_head_risk": 0.5,

    # ===== 串口 =====
    "serial_port": "COM3",
    "serial_baud": 115200,
    "serial_enabled": True,

    # ===== 深度学习模型（可选） =====
    "use_neural": False,
    "neural_model": "EfficientPhys",
    "neural_frame_depth": 10,
    "neural_img_size": 36,
    "neural_model_path": "",        # 预训练权重路径

    # ===== GUI =====
    "show_gui": True,
    "show_bvp_plot": True,
}
