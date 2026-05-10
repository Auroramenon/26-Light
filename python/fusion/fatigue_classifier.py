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
        # 自动恢复机制：记录进入当前等级的时间
        self._level_enter_time = None
        self._auto_reset_enabled = config.get("auto_reset_enabled", True)
        self._auto_reset_durations = config.get("auto_reset_durations", {
            1: 5.0,   # Level 1 持续5秒后自动恢复
            2: 5.0,   # Level 2 持续5秒后自动恢复
            3: 7.0    # Level 3 持续7秒后自动恢复
        })

    def update(self, fatigue_score, risks=None):
        """根据平滑后的疲劳评分和各路风险分输出疲劳等级

        Args:
            fatigue_score: [0, 1] EMA 平滑后的综合评分
            risks: dict {"hrv", "perclos", "yawn", "head"} 各路 Risk 分

        Returns:
            level: 0=正常, 1=轻度, 2=中度, 3=重度
        """
        cfg = self.cfg
        up = cfg.get("upgrade_thresholds", [0.35, 0.55, 0.75])
        down = cfg.get("downgrade_thresholds", [0.25, 0.45, 0.65])
        hold = cfg.get("hold_seconds", 3)

        now = time.time()

        # --- 自动恢复机制：在疲劳等级持续一定时间后自动恢复到Level 0 ---
        if self._auto_reset_enabled and self.current_level > 0:
            if self._level_enter_time is not None:
                duration = now - self._level_enter_time
                reset_duration = self._auto_reset_durations.get(self.current_level, 5.0)

                if duration >= reset_duration:
                    # 持续时间到达，自动恢复到Level 0
                    self.current_level = 0
                    self._candidate_level = 0
                    self._candidate_since = now
                    self._level_enter_time = now
                    return self.current_level

        # --- 快速恢复机制：评分很低时快速降至 Level 0 ---
        if cfg.get("quick_recovery", True):
            recovery_threshold = cfg.get("recovery_threshold", 0.20)
            if fatigue_score < recovery_threshold and self.current_level > 0:
                # 评分很低，快速恢复到正常状态
                self.current_level = 0
                self._candidate_level = 0
                self._candidate_since = now
                self._level_enter_time = now
                return self.current_level

        # --- 迟滞阈值判定目标等级 ---
        target = self._hysteresis_level(fatigue_score, up, down)

        # --- Level 3 多证据要求 ---
        if target == 3 and cfg.get("level3_multi_evidence", True) and risks:
            if not self._check_multi_evidence(risks, cfg):
                target = 2  # 证据不足，降为 Level 2

        # --- 持续性约束 ---
        if target != self._candidate_level:
            self._candidate_level = target
            self._candidate_since = now

        if target != self.current_level:
            if self._candidate_since is not None and (now - self._candidate_since) >= hold:
                # 等级发生变化
                old_level = self.current_level
                self.current_level = target

                # 记录进入新等级的时间（用于自动恢复）
                if self.current_level != old_level:
                    self._level_enter_time = now
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
    def _check_multi_evidence(risks, cfg):
        """Level 3 需要至少一路强证据（阈值可由配置调整）

        更严格的多证据判定逻辑，避免误判重度疲劳：
        1. PERCLOS是最可靠的疲劳指标，需要达到很高阈值
        2. HRV作为生理指标，需要较高阈值才能确认
        3. 哈欠+低头的组合指标，两者同时出现才有说服力
        """
        # 强证据1：PERCLOS达到高风险（最可靠）
        if risks.get("perclos", 0) >= cfg.get("level3_min_perclos_risk", 0.90):
            return True

        # 强证据2：HRV达到高风险
        if risks.get("hrv", 0) >= cfg.get("level3_min_hrv_risk", 0.80):
            return True

        # 强证据3：哈欠+低头组合（两者都需要较高）
        if (risks.get("yawn", 0) >= cfg.get("level3_min_yawn_risk", 0.70)
                and risks.get("head", 0) >= cfg.get("level3_min_head_risk", 0.60)):
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
