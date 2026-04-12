#ifndef __FATIGUE_FEEDBACK_H
#define __FATIGUE_FEEDBACK_H

#include <stdint.h>

/* 疲劳等级 */
typedef enum {
    FATIGUE_NORMAL   = 0,   /* 正常 — 绿色常亮，静音 */
    FATIGUE_MILD     = 1,   /* 轻度 — 黄色常亮，慢间歇蜂鸣 */
    FATIGUE_MODERATE = 2,   /* 中度 — 橙色常亮，快间歇蜂鸣 */
    FATIGUE_SEVERE   = 3,   /* 重度 — 红色闪烁，持续报警 */
} FatigueLevel;

/* 初始化反馈系统 */
void Feedback_Init(void);

/* 设置疲劳等级（更新 LED 和蜂鸣器） */
void Feedback_SetLevel(FatigueLevel level);

/* 定时更新（主循环每 1ms 调用，处理闪烁等动态效果） */
void Feedback_Tick(uint32_t now_ms);

#endif /* __FATIGUE_FEEDBACK_H */
