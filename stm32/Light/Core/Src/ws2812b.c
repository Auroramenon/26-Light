/**
 * WS2812B LED 灯带驱动 — TIM2_CH1 PWM + DMA
 *
 * 原理: WS2812B 使用 800kHz 单线协议，每个 bit 用不同占空比的 PWM 表示。
 * TIM2 配置为 800kHz PWM (72MHz / 90 = 800kHz, ARR=89)，
 * 通过 DMA 逐 bit 更新 CCR 值实现数据传输。
 */

#include "ws2812b.h"
#include <string.h>

/* DMA 缓冲区: 每个 LED 24 bit (GRB) + 复位段 */
#define DMA_BUF_SIZE  (WS2812B_NUM_LEDS * 24 + WS2812B_RESET_SLOTS)
static uint16_t dma_buffer[DMA_BUF_SIZE];

/* LED 颜色数据 (RGB) */
static uint8_t led_r[WS2812B_NUM_LEDS];
static uint8_t led_g[WS2812B_NUM_LEDS];
static uint8_t led_b[WS2812B_NUM_LEDS];

static TIM_HandleTypeDef *ws_htim;
static uint32_t ws_channel;
static volatile uint8_t dma_busy = 0;
static volatile uint32_t dma_start_tick = 0;

void WS2812B_Init(TIM_HandleTypeDef *htim, uint32_t channel)
{
    ws_htim = htim;
    ws_channel = channel;
    memset(dma_buffer, 0, sizeof(dma_buffer));
    WS2812B_Clear();
}

void WS2812B_SetColor(uint8_t index, uint8_t r, uint8_t g, uint8_t b)
{
    if (index >= WS2812B_NUM_LEDS) return;
    led_r[index] = r;
    led_g[index] = g;
    led_b[index] = b;
}

void WS2812B_Fill(uint8_t r, uint8_t g, uint8_t b)
{
    for (uint8_t i = 0; i < WS2812B_NUM_LEDS; i++) {
        led_r[i] = r;
        led_g[i] = g;
        led_b[i] = b;
    }
}

void WS2812B_Clear(void)
{
    WS2812B_Fill(0, 0, 0);
}

void WS2812B_Update(void)
{
    /* 超时保护: 如果 dma_busy 卡死超过 5ms，强制复位 */
    if (dma_busy) {
        if (HAL_GetTick() - dma_start_tick > 5) {
            HAL_TIM_PWM_Stop_DMA(ws_htim, ws_channel);
            dma_busy = 0;
        } else {
            return;
        }
    }

    uint16_t idx = 0;

    /* 编码每个 LED 的 GRB 数据 (WS2812B 是 GRB 顺序) */
    for (uint8_t led = 0; led < WS2812B_NUM_LEDS; led++) {
        uint8_t colors[3] = { led_g[led], led_r[led], led_b[led] };
        for (uint8_t c = 0; c < 3; c++) {
            for (int8_t bit = 7; bit >= 0; bit--) {
                dma_buffer[idx++] = (colors[c] & (1 << bit))
                    ? WS2812B_BIT1 : WS2812B_BIT0;
            }
        }
    }

    /* 复位段: 全 0 (低电平 > 50us) */
    for (uint16_t i = 0; i < WS2812B_RESET_SLOTS; i++) {
        dma_buffer[idx++] = 0;
    }

    dma_busy = 1;
    dma_start_tick = HAL_GetTick();
    HAL_TIM_PWM_Start_DMA(ws_htim, ws_channel,
                           (uint32_t *)dma_buffer, DMA_BUF_SIZE);
}

void WS2812B_DMA_Callback(void)
{
    HAL_TIM_PWM_Stop_DMA(ws_htim, ws_channel);
    dma_busy = 0;
}
