"""四级疲劳分类器 — 迟滞 + 持续性约束 + Level 3 多证据"""

import time


class FatigueClassifier:
    """带迟滞、持续性约束和多证据要求的有状态疲劳分类器"""

    def __init__(self, config):
        self.cfg = config
        self.current_level = 0
        # 候选等级及其首次触发时间
        self._candidate_level = 0
        self._candidate_since = None

    def update(self, fatigue_score, risks=None):
        """根据平滑后的疲劳评分和各路风险分输出疲劳等级

        Args:
            fatigue_score: [0, 1] EMA 平滑后的综合评分
            risks: dict {"hrv", "perclos", "yawn", "head"} 各路 Risk 分

        Returns:
            level: 0=正常, 1=轻度, 2=中度, 3=重度
        """
        cfg = self.cfg
        up = cfg.get("upgrade_thresholds", [0.30, 0.50, 0.70])
        down = cfg.get("downgrade_thresholds", [0.25, 0.45, 0.65])
        hold = cfg.get("hold_seconds", 5)

        # --- 迟滞阈值判定目标等级 ---
        target = self._hysteresis_level(fatigue_score, up, down)

        # --- Level 3 多证据要求 ---
        if target == 3 and cfg.get("level3_multi_evidence", True) and risks:
            if not self._check_multi_evidence(risks):
                target = 2  # 证据不足，降为 Level 2

        # --- 持续性约束 ---
        now = time.time()
        if target != self._candidate_level:
            self._candidate_level = target
            self._candidate_since = now

        if target != self.current_level:
            if self._candidate_since is not None and (now - self._candidate_since) >= hold:
                self.current_level = target
        else:
            # 已经在目标等级，重置候选
            self._candidate_level = self.current_level
            self._candidate_since = now

        return self.current_level

    def _hysteresis_level(self, score, up_thresholds, down_thresholds):
        """迟滞阈值判定：升级用 up，降级用 down"""
        cur = self.current_level

        if cur == 0:
            if score >= up_thresholds[0]:
                if score >= up_thresholds[2]:
                    return 3
                if score >= up_thresholds[1]:
                    return 2
                return 1
            return 0

        if cur == 1:
            if score < down_thresholds[0]:
                return 0
            if score >= up_thresholds[1]:
                if score >= up_thresholds[2]:
                    return 3
                return 2
            return 1

        if cur == 2:
            if score < down_thresholds[1]:
                if score < down_thresholds[0]:
                    return 0
                return 1
            if score >= up_thresholds[2]:
                return 3
            return 2

        # cur == 3
        if score < down_thresholds[2]:
            if score < down_thresholds[1]:
                if score < down_thresholds[0]:
                    return 0
                return 1
            return 2
        return 3

    @staticmethod
    def _check_multi_evidence(risks):
        """Level 3 需要至少一路强证据"""
        if risks.get("perclos", 0) >= 1.0:
            return True
        if risks.get("hrv", 0) >= 0.7:
            return True
        if risks.get("yawn", 0) >= 0.5 and risks.get("head", 0) >= 0.5:
            return True
        return False


# === 兼容旧接口 ===
def classify_fatigue(fatigue_score, config):
    """无状态兼容接口（行为与旧版一致，无迟滞/持续性）"""
    thresholds = config["fatigue_thresholds"]
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
