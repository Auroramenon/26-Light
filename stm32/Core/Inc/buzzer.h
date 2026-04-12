#ifndef __BUZZER_H
#define __BUZZER_H

#include "main.h"
#include <stdint.h>

/* 蜂鸣器模式 */
typedef enum {
    BUZZER_OFF = 0,         /* 静音 */
    BUZZER_SLOW,            /* 慢间歇: 1s 响 / 2s 停 */
    BUZZER_FAST,            /* 快间歇: 300ms 响 / 300ms 停 */
    BUZZER_CONTINUOUS,      /* 持续报警 */
} BuzzerMode;

/* 初始化蜂鸣器 PWM */
void Buzzer_Init(TIM_HandleTypeDef *htim, uint32_t channel);

/* 设置蜂鸣器模式 */
void Buzzer_SetMode(BuzzerMode mode);

/* 蜂鸣器定时更新（在 SysTick 或主循环中调用，每 1ms 一次） */
void Buzzer_Tick(uint32_t now_ms);

#endif /* __BUZZER_H */
