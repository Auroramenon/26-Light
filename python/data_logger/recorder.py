"""实时数据记录器 — 采集测试过程中的HR、HRV、行为特征等数据"""

import os
import time
import json
import csv
from datetime import datetime
from collections import deque


class DataRecorder:
    """实时数据记录器

    功能：
    1. 实时记录HR、HRV、PERCLOS、哈欠率、头姿、疲劳等级等数据
    2. 保存为CSV格式，便于后续分析
    3. 同时保存JSON格式的元数据和配置信息
    4. 支持暂停/恢复记录
    """

    def __init__(self, output_dir="test_data", session_name=None, sample_interval=1.0):
        """初始化数据记录器

        Args:
            output_dir: 输出目录路径
            session_name: 测试会话名称（默认使用时间戳）
            sample_interval: 采样间隔（秒），默认1.0秒记录一次
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 生成会话名称
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name

        # 文件路径
        self.csv_path = os.path.join(output_dir, f"{session_name}_data.csv")
        self.meta_path = os.path.join(output_dir, f"{session_name}_meta.json")

        # 采样控制
        self.sample_interval = sample_interval
        self.last_record_time = 0.0
        self.pending_data = []  # 待处理的数据（在采样间隔内收集）

        # 数据缓冲区
        self.data_buffer = deque(maxlen=10000)  # 最多保存10000条记录

        # 记录状态
        self.is_recording = True
        self.start_time = time.time()
        self.record_count = 0

        # 元数据
        self.metadata = {
            "session_name": session_name,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_records": 0,
            "sample_interval": sample_interval,
            "config": {}
        }

        # 初始化CSV文件
        self._init_csv()

        print(f"[数据记录] 会话开始: {session_name}")
        print(f"[数据记录] 采样间隔: {sample_interval}秒")
        print(f"[数据记录] 数据文件: {self.csv_path}")

    def _init_csv(self):
        """初始化CSV文件，写入表头"""
        headers = [
            "timestamp",           # 时间戳（秒）
            "datetime",            # 日期时间字符串
            "elapsed_time",        # 从开始到现在的时间（秒）
            "hr",                  # 心率 (BPM)
            "hrv_rmssd",          # HRV RMSSD (ms)
            "hrv_sdnn",           # HRV SDNN (ms)
            "hrv_pnn50",          # HRV pNN50 (%)
            "hrv_lf_hf",          # HRV LF/HF比值
            "hrv_valid",          # HRV数据是否有效
            "hrv_ibi_count",      # IBI数量
            "perclos",            # PERCLOS (0-1)
            "yawn_rate",          # 哈欠率 (次/分)
            "head_pitch",         # 头部俯仰角度（度）
            "fatigue_score",      # 综合疲劳评分 (0-1)
            "fatigue_level",      # 疲劳等级 (0-3)
            "risk_hrv",           # HRV风险分 (0-1)
            "risk_perclos",       # PERCLOS风险分 (0-1)
            "risk_yawn",          # 哈欠风险分 (0-1)
            "risk_head",          # 头姿风险分 (0-1)
        ]

        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    def record(self, data_dict):
        """记录一条数据（采样控制）

        Args:
            data_dict: 包含各项指标的字典，例如：
                {
                    "hr": 75.0,
                    "hrv_features": {...},
                    "perclos": 0.15,
                    "yawn_rate": 0.3,
                    "head_pitch": 5.0,
                    "fatigue_score": 0.35,
                    "fatigue_level": 1,
                    "risks": {...}
                }
        """
        if not self.is_recording:
            return

        now = time.time()

        # 将数据添加到待处理列表
        self.pending_data.append((now, data_dict))

        # 检查是否到达采样间隔
        if now - self.last_record_time >= self.sample_interval:
            # 从待处理数据中选择最具代表性的一条
            if self.pending_data:
                selected_data = self._select_representative_data()
                self._write_record(selected_data)
                self.pending_data.clear()
                self.last_record_time = now

    def _select_representative_data(self):
        """从待处理数据中选择最具代表性的一条

        策略：选择疲劳等级最高的数据，如果等级相同则选择评分最高的
        这样可以确保不会遗漏重要的疲劳信号
        """
        if not self.pending_data:
            return None

        # 按疲劳等级和评分排序，选择最严重的状态
        selected = max(self.pending_data,
                      key=lambda x: (x[1].get("fatigue_level", 0),
                                   x[1].get("fatigue_score", 0)))
        return selected

    def _write_record(self, data_tuple):
        """写入一条记录到CSV文件

        Args:
            data_tuple: (timestamp, data_dict)
        """
        if data_tuple is None:
            return

        now, data_dict = data_tuple
        elapsed = now - self.start_time

        # 提取HRV特征
        hrv = data_dict.get("hrv_features", {})
        risks = data_dict.get("risks", {})

        # 构建记录行
        record = {
            "timestamp": now,
            "datetime": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "elapsed_time": round(elapsed, 2),
            "hr": round(data_dict.get("hr", 0.0), 1),
            "hrv_rmssd": round(hrv.get("rmssd", 0.0), 2),
            "hrv_sdnn": round(hrv.get("sdnn", 0.0), 2),
            "hrv_pnn50": round(hrv.get("pnn50", 0.0), 2),
            "hrv_lf_hf": round(hrv.get("lf_hf", 0.0), 3),
            "hrv_valid": hrv.get("valid", False),
            "hrv_ibi_count": hrv.get("ibi_count", 0),
            "perclos": round(data_dict.get("perclos", 0.0), 3),
            "yawn_rate": round(data_dict.get("yawn_rate", 0), 2),
            "head_pitch": round(data_dict.get("head_pitch", 0.0), 2),
            "fatigue_score": round(data_dict.get("fatigue_score", 0.0), 3),
            "fatigue_level": data_dict.get("fatigue_level", 0),
            "risk_hrv": round(risks.get("hrv", 0.0), 3),
            "risk_perclos": round(risks.get("perclos", 0.0), 3),
            "risk_yawn": round(risks.get("yawn", 0.0), 3),
            "risk_head": round(risks.get("head", 0.0), 3),
        }

        # 添加到缓冲区
        self.data_buffer.append(record)
        self.record_count += 1

        # 写入CSV文件
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            writer.writerow(record)

    def pause(self):
        """暂停记录"""
        self.is_recording = False
        print("[数据记录] 已暂停")

    def resume(self):
        """恢复记录"""
        self.is_recording = True
        print("[数据记录] 已恢复")

    def set_config(self, config):
        """保存配置信息到元数据"""
        self.metadata["config"] = {
            "camera_fps": config.get("camera_fps"),
            "signal_window_sec": config.get("signal_window_sec"),
            "hrv_window_sec": config.get("hrv_window_sec"),
            "rppg_method": config.get("rppg_method"),
            "face_det_backend": config.get("face_det_backend"),
            "fatigue_thresholds": config.get("fatigue_thresholds"),
            "upgrade_thresholds": config.get("upgrade_thresholds"),
            "downgrade_thresholds": config.get("downgrade_thresholds"),
            "weights": {
                "w_hrv": config.get("w_hrv"),
                "w_perclos": config.get("w_perclos"),
                "w_yawn": config.get("w_yawn"),
                "w_head": config.get("w_head"),
            }
        }

    def close(self):
        """关闭记录器，保存元数据"""
        self.metadata["end_time"] = datetime.now().isoformat()
        self.metadata["total_records"] = self.record_count

        # 保存元数据
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        print(f"[数据记录] 会话结束: {self.session_name}")
        print(f"[数据记录] 总记录数: {self.record_count}")
        print(f"[数据记录] 元数据文件: {self.meta_path}")

    def get_summary(self):
        """获取当前记录的摘要信息"""
        if len(self.data_buffer) == 0:
            return "暂无数据"

        elapsed = time.time() - self.start_time
        return (f"会话: {self.session_name} | "
                f"记录数: {self.record_count} | "
                f"时长: {elapsed:.0f}秒 | "
                f"状态: {'记录中' if self.is_recording else '已暂停'}")
