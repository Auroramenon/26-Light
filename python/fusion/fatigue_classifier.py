"""四级疲劳分类器"""


def classify_fatigue(fatigue_score, config):
    """根据综合疲劳评分输出疲劳等级

    Args:
        fatigue_score: [0, 1] 综合评分
        config: 配置字典

    Returns:
        level: 0=正常, 1=轻度, 2=中度, 3=重度
    """
    thresholds = config["fatigue_thresholds"]  # [0.3, 0.5, 0.7]

    if fatigue_score < thresholds[0]:
        return 0
    elif fatigue_score < thresholds[1]:
        return 1
    elif fatigue_score < thresholds[2]:
        return 2
    else:
        return 3


LEVEL_NAMES = {0: "正常", 1: "轻度疲劳", 2: "中度疲劳", 3: "重度疲劳"}
LEVEL_COLORS_BGR = {0: (0, 200, 0), 1: (0, 200, 200), 2: (0, 140, 255), 3: (0, 0, 255)}
