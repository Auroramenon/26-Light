#ifndef __WS2812B_H
#define __WS2812B_H

#include "main.h"
#include <stdint.h>

/* WS2812B 配置 */
#define WS2812B_NUM_LEDS    8       /* LED 数量 */
#define WS2812B_BIT0        36      /* 0 码占空比 (ARR=89, ~0.4us) */
#define WS2812B_BIT1        64      /* 1 码占空比 (ARR=89, ~0.8us) */
#define WS2812B_RESET_SLOTS 50      /* 复位低电平周期数 (>50us) */

/* 初始化 */
void WS2812B_Init(TIM_HandleTypeDef *htim, uint32_t channel);

/* 设置单个 LED 颜色 (GRB 顺序) */
void WS2812B_SetColor(uint8_t index, uint8_t r, uint8_t g, uint8_t b);

/* 所有 LED 设为同一颜色 */
void WS2812B_Fill(uint8_t r, uint8_t g, uint8_t b);

/* 关闭所有 LED */
void WS2812B_Clear(void);

/* 触发 DMA 传输更新 LED */
void WS2812B_Update(void);

/* DMA 传输完成回调（内部使用） */
void WS2812B_DMA_Callback(void);

#endif /* __WS2812B_H */
