/**
 * 疲劳反馈状态机 — 将疲劳等级映射到 LED 颜色和蜂鸣器模式
 */

#include "fatigue_feedback.h"
#include "ws2812b.h"
#include "buzzer.h"

static FatigueLevel current_level = FATIGUE_NORMAL;
static uint32_t blink_timer = 0;
static uint8_t  blink_state = 0;  /* 0=亮, 1=灭 (用于重度闪烁) */

void Feedback_Init(void)
{
    current_level = FATIGUE_NORMAL;
    WS2812B_Fill(0, 200, 0);  /* 绿色 */
    WS2812B_Update();
    Buzzer_SetMode(BUZZER_OFF);
}

void Feedback_SetLevel(FatigueLevel level)
{
    if (level == current_level) return;
    current_level = level;
    blink_timer = 0;
    blink_state = 0;

    switch (level) {
    case FATIGUE_NORMAL:
        WS2812B_Fill(0, 200, 0);      /* 绿色 */
        WS2812B_Update();
        Buzzer_SetMode(BUZZER_OFF);
        break;

    case FATIGUE_MILD:
        WS2812B_Fill(255, 200, 0);    /* 黄色 */
        WS2812B_Update();
        Buzzer_SetMode(BUZZER_SLOW);
        break;

    case FATIGUE_MODERATE:
        WS2812B_Fill(255, 100, 0);    /* 橙色 */
        WS2812B_Update();
        Buzzer_SetMode(BUZZER_FAST);
        break;

    case FATIGUE_SEVERE:
        WS2812B_Fill(255, 0, 0);      /* 红色 */
        WS2812B_Update();
        Buzzer_SetMode(BUZZER_CONTINUOUS);
        break;
    }
}

void Feedback_Tick(uint32_t now_ms)
{
    /* 蜂鸣器节拍 */
    Buzzer_Tick(now_ms);

    /* 重度疲劳: LED 红色闪烁 (500ms 周期) */
    if (current_level == FATIGUE_SEVERE) {
        if (now_ms - blink_timer >= 500) {
            blink_timer = now_ms;
            blink_state = !blink_state;
            if (blink_state) {
                WS2812B_Clear();
            } else {
                WS2812B_Fill(255, 0, 0);
            }
            WS2812B_Update();
        }
    }
}
