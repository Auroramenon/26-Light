"""全局配置参数"""

import os

# rPPG-Toolbox 路径
RPPG_TOOLBOX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "rPPG-Toolbox"))

CONFIG = {
    # ===== 相机 =====
    "camera_index": 1,              # LRCP S400 USB设备索引（或设备路径字符串）
    "camera_fps": 30,
    "camera_width": 640,
    "camera_height": 480,
    "is_nir_camera": True,          # 是否为近红外相机（850nm）

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
    "signal_window_sec": 10,        # 滑动窗口长度（秒）NIR模式建议10秒以上
    "rppg_method": "NIR_ADV",       # RGB模式: "CHROM"/"POS", NIR模式: "NIR"/"NIR_ADV"/"NIR_ROBUST"
    "bandpass_low": 0.7,            # Hz (42 BPM)
    "bandpass_high": 4.0,           # Hz (240 BPM)

    # ===== HRV =====
    "hrv_window_sec": 60,           # HRV计算窗口（秒）
    "hrv_update_interval_sec": 1.0, # HRV更新间隔（秒）
    "nir_hrv_mode": "simplified",   # NIR模式HRV计算: "simplified"(仅心率) / "trend"(趋势) / "full"(完整)
    "hrv_min_ibi_count": 40,        # 最少IBI数量（少于此值HRV不可靠）

    # ===== 行为检测 =====
    "ear_threshold": 0.2,           # Eye Aspect Ratio 闭眼阈值
    "perclos_window_sec": 60,       # PERCLOS统计窗口（秒）
    "yawn_mar_threshold": 0.6,      # Mouth Aspect Ratio 哈欠阈值
    "yawn_min_frames": 10,          # 连续超阈值帧数才算一次哈欠
    "yawn_window_sec": 45.0,        # 哈欠统计窗口（秒，从60秒缩短到45秒）
    "yawn_decay_enabled": True,     # 启用哈欠衰减机制
    "yawn_decay_window": 15.0,      # 哈欠记录15秒后开始衰减（从30秒缩短）
    "head_pitch_threshold": 15.0,   # 兼容旧键（建议改用 head_angle_low）

    # ===== 风险映射参数（分段线性） =====
    "perclos_low": 0.15,            # PERCLOS 低于此值 Risk=0
    "perclos_high": 0.30,           # PERCLOS 高于此值 Risk=1
    "yawn_rate_low": 0.3,           # 哈欠频率低于此值 Risk=0 (次/分，提高阈值)
    "yawn_rate_high": 1.2,          # 哈欠频率高于此值 Risk=1 (次/分，提高阈值)
    "head_angle_low": 15.0,         # 头姿偏转低于此值 Risk=0 (度)
    "head_angle_high": 35.0,        # 头姿偏转高于此值 Risk=1 (度)

    # ===== 多模态融合权重 =====
    # NIR模式下HRV准确度较低，降低其权重，提高行为指标权重
    "w_hrv": 0.20,          # HRV权重（NIR模式建议0.15-0.20）
    "w_perclos": 0.50,      # PERCLOS权重（主要指标，提高）
    "w_yawn": 0.15,         # 哈欠权重（降低，避免单次哈欠影响过大）
    "w_head": 0.15,         # 头姿权重

    # ===== EMA 时间平滑 =====
    "ema_alpha": 0.3,               # EMA 平滑系数 (0.2~0.4, 越小越平滑)

    # ===== 疲劳分级阈值 =====
    "fatigue_thresholds": [0.35, 0.55, 0.75],           # 基础阈值（兼容旧版）
    "upgrade_thresholds": [0.35, 0.55, 0.75],           # 升级阈值（更符合实际）
    "downgrade_thresholds": [0.25, 0.45, 0.65],         # 降级阈值（差距0.10，更容易降级）
    "hold_seconds": 3,                                   # 持续性约束（秒，缩短以更快响应）
    "level3_multi_evidence": True,                       # Level 3 是否要求多证据
    "quick_recovery": True,                              # 启用快速恢复机制
    "recovery_threshold": 0.20,                          # 快速恢复阈值（低于此值快速降至level0）

    # ===== 自动恢复机制（防止长时间响铃） =====
    "auto_reset_enabled": True,                          # 启用自动恢复到Level 0
    "auto_reset_durations": {                            # 各等级持续多久后自动恢复（秒）
        1: 5.0,   # Level 1 持续5秒后自动恢复到Level 0
        2: 5.0,   # Level 2 持续5秒后自动恢复到Level 0
        3: 7.0    # Level 3 持续7秒后自动恢复到Level 0
    },

    # Level 3 多证据阈值（更严格，避免误判）
    # 规则：满足其一即可进入 Level 3：
    # 1) PERCLOS 风险 >= level3_min_perclos_risk (主要指标)
    # 2) HRV 风险 >= level3_min_hrv_risk (辅助指标)
    # 3) 哈欠风险 >= level3_min_yawn_risk 且 低头风险 >= level3_min_head_risk (组合指标)
    "level3_min_perclos_risk": 0.90,    # 提高阈值，PERCLOS需达到90%才判定重度疲劳
    "level3_min_hrv_risk": 0.80,        # 提高阈值，确保HRV确实显示高疲劳
    "level3_min_yawn_risk": 0.70,       # 提高阈值，避免误判
    "level3_min_head_risk": 0.60,       # 提高阈值

    # ===== 串口 =====
    "serial_port": "COM3",
    "serial_baud": 115200,
    "serial_enabled": True,
    "serial_send_interval_sec": 0.5,      # 最小发送间隔（秒）
    "serial_reconnect_interval_sec": 2.0, # 断线重连周期（秒）
    "serial_max_failures": 5,             # 连续发送失败上限

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
