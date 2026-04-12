/**
 * 蜂鸣器控制 — TIM3_CH1 PWM
 *
 * 高电平有源蜂鸣器：PWM 占空比 50% 时发声，0% 时静音。
 * 通过改变开/关时间实现不同报警模式。
 */

#include "buzzer.h"

static TIM_HandleTypeDef *buz_htim;
static uint32_t buz_channel;
static BuzzerMode current_mode = BUZZER_OFF;

/* 模式参数: on_ms, off_ms (0 = 持续) */
static const struct {
    uint16_t on_ms;
    uint16_t off_ms;
} mode_params[] = {
    [BUZZER_OFF]        = { 0,    0    },
    [BUZZER_SLOW]       = { 1000, 2000 },
    [BUZZER_FAST]       = { 300,  300  },
    [BUZZER_CONTINUOUS] = { 0,    0    },  /* 特殊处理: 常开 */
};

static uint32_t toggle_time = 0;
static uint8_t  buzzer_on = 0;

void Buzzer_Init(TIM_HandleTypeDef *htim, uint32_t channel)
{
    buz_htim = htim;
    buz_channel = channel;
    HAL_TIM_PWM_Start(htim, channel);
    __HAL_TIM_SET_COMPARE(htim, channel, 0);  /* 初始静音 */
}

void Buzzer_SetMode(BuzzerMode mode)
{
    current_mode = mode;
    toggle_time = 0;
    buzzer_on = 0;

    if (mode == BUZZER_OFF) {
        __HAL_TIM_SET_COMPARE(buz_htim, buz_channel, 0);
    } else if (mode == BUZZER_CONTINUOUS) {
        /* 50% 占空比持续发声 */
        uint32_t arr = __HAL_TIM_GET_AUTORELOAD(buz_htim);
        __HAL_TIM_SET_COMPARE(buz_htim, buz_channel, arr / 2);
        buzzer_on = 1;
    }
}

void Buzzer_Tick(uint32_t now_ms)
{
    if (current_mode == BUZZER_OFF || current_mode == BUZZER_CONTINUOUS)
        return;

    uint16_t on_t  = mode_params[current_mode].on_ms;
    uint16_t off_t = mode_params[current_mode].off_ms;

    if (now_ms - toggle_time >= (buzzer_on ? on_t : off_t)) {
        toggle_time = now_ms;
        buzzer_on = !buzzer_on;

        if (buzzer_on) {
            uint32_t arr = __HAL_TIM_GET_AUTORELOAD(buz_htim);
            __HAL_TIM_SET_COMPARE(buz_htim, buz_channel, arr / 2);
        } else {
            __HAL_TIM_SET_COMPARE(buz_htim, buz_channel, 0);
        }
    }
}
