"""NIR模式下的HRV风险评估优化模块

针对近红外rPPG的HRV准确度限制，提供三种计算模式：
1. simplified: 仅使用心率(HR)，忽略HRV细节指标
2. trend: 使用HRV趋势而非绝对值
3. full: 完整HRV计算（与RGB模式相同）

作者：26-Light项目组
"""

import numpy as np
from collections import deque


class NIRHRVRiskCalculator:
    """NIR模式下的HRV风险计算器"""

    def __init__(self, config):
        self.mode = config.get("nir_hrv_mode", "simplified")
        self.is_nir = config.get("is_nir_camera", False)
        self.min_ibi_count = config.get("hrv_min_ibi_count", 40)

        # 趋势模式下的历史记录
        if self.mode == "trend":
            self.hrv_history = deque(maxlen=10)  # 保存最近10次HRV值

    def calculate_risk(self, hrv_features):
        """计算HRV风险分 [0, 1]

        Args:
            hrv_features: dict, 包含 rmssd, sdnn, lf_hf, mean_hr, ibi_count, valid

        Returns:
            risk: float [0, 1]
        """
        if not hrv_features.get("valid", False):
            return 0.0  # 数据不可靠时返回低风险（避免误报）

        # IBI数量不足，不可靠
        if hrv_features.get("ibi_count", 0) < self.min_ibi_count:
            return 0.0

        # 根据模式选择计算方法
        if self.mode == "simplified":
            return self._calculate_hr_only(hrv_features)
        elif self.mode == "trend":
            return self._calculate_trend(hrv_features)
        else:  # "full"
            return self._calculate_full(hrv_features)

    def _calculate_hr_only(self, hrv_features):
        """简化模式：仅使用心率判断

        疲劳时心率特征：
        - 静息心率偏低（<55 BPM）或偏高（>90 BPM）
        - 正常范围：55-90 BPM
        """
        hr = hrv_features.get("mean_hr", 70.0)

        if hr < 50:
            return 0.8  # 心率过低，可能极度疲劳
        elif hr < 55:
            return 0.5  # 心率偏低
        elif hr > 95:
            return 0.7  # 心率过高，可能压力/疲劳
        elif hr > 90:
            return 0.4  # 心率偏高
        else:
            return 0.0  # 心率正常

    def _calculate_trend(self, hrv_features):
        """趋势模式：关注HRV变化趋势而非绝对值

        疲劳时HRV趋势：
        - RMSSD持续下降
        - SDNN持续下降
        """
        rmssd = hrv_features.get("rmssd", 30.0)
        sdnn = hrv_features.get("sdnn", 50.0)

        # 记录当前值
        self.hrv_history.append({
            "rmssd": rmssd,
            "sdnn": sdnn
        })

        # 历史数据不足，无法计算趋势
        if len(self.hrv_history) < 5:
            return 0.0

        # 提取历史序列
        rmssd_seq = [h["rmssd"] for h in self.hrv_history]
        sdnn_seq = [h["sdnn"] for h in self.hrv_history]

        # 计算线性趋势（斜率）
        x = np.arange(len(rmssd_seq))
        rmssd_trend = np.polyfit(x, rmssd_seq, 1)[0]  # 斜率
        sdnn_trend = np.polyfit(x, sdnn_seq, 1)[0]

        # 趋势评分
        risk = 0.0

        # RMSSD下降趋势
        if rmssd_trend < -1.0:  # 快速下降
            risk += 0.4
        elif rmssd_trend < -0.3:  # 缓慢下降
            risk += 0.2

        # SDNN下降趋势
        if sdnn_trend < -1.5:
            risk += 0.4
        elif sdnn_trend < -0.5:
            risk += 0.2

        # 当前绝对值也作为参考（权重较低）
        if rmssd < 20:
            risk += 0.1
        if sdnn < 30:
            risk += 0.1

        return min(risk, 1.0)

    def _calculate_full(self, hrv_features):
        """完整模式：使用所有HRV指标（与RGB模式相同）

        这是原始的HRV风险计算方法
        """
        rmssd = hrv_features.get("rmssd", 30.0)
        sdnn = hrv_features.get("sdnn", 50.0)
        lf_hf = hrv_features.get("lf_hf", 1.0)

        # RMSSD评分：正常20-50ms，疲劳<20ms
        if rmssd < 15:
            rmssd_score = 1.0
        elif rmssd < 40:
            rmssd_score = (40 - rmssd) / 25.0
        else:
            rmssd_score = 0.0

        # SDNN评分：正常50-100ms，疲劳<30ms
        if sdnn < 25:
            sdnn_score = 1.0
        elif sdnn < 80:
            sdnn_score = (80 - sdnn) / 55.0
        else:
            sdnn_score = 0.0

        # LF/HF评分：正常0.5-2.0，疲劳>3.0
        if lf_hf > 4.0:
            lfhf_score = 1.0
        elif lf_hf > 1.0:
            lfhf_score = (lf_hf - 1.0) / 3.0
        else:
            lfhf_score = 0.0

        # 加权融合
        risk = 0.4 * rmssd_score + 0.3 * sdnn_score + 0.3 * lfhf_score
        return risk


def create_hrv_risk_calculator(config):
    """工厂函数：根据配置创建HRV风险计算器

    Args:
        config: dict, 配置字典

    Returns:
        NIRHRVRiskCalculator 实例
    """
    return NIRHRVRiskCalculator(config)
