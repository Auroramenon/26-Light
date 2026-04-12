/**
 * 疲劳驾驶光电预警系统 — STM32F103C8T6 主程序
 *
 * 外设:
 *   USART1 (PA9/PA10) — 接收 PC 端疲劳等级数据 (115200, 8N1)
 *   TIM2_CH1 (PA0)    — WS2812B LED 灯带 PWM+DMA
 *   TIM3_CH1 (PA6)    — 蜂鸣器 PWM
 */

#include "main.h"
#include "ws2812b.h"
#include "buzzer.h"
#include "uart_protocol.h"
#include "fatigue_feedback.h"
#include <stdio.h>

/* 外设句柄 */
UART_HandleTypeDef huart1;
TIM_HandleTypeDef  htim2;
TIM_HandleTypeDef  htim3;
DMA_HandleTypeDef  hdma_tim2_ch1;

/* 前向声明 */
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_TIM2_Init(void);
static void MX_TIM3_Init(void);

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* 初始化外设 (DMA 必须在 TIM 之前) */
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();
    MX_TIM2_Init();
    MX_TIM3_Init();

    /* 初始化应用模块 */
    WS2812B_Init(&htim2, TIM_CHANNEL_1);
    Buzzer_Init(&htim3, TIM_CHANNEL_1);
    UART_Protocol_Init(&huart1);
    Feedback_Init();

    /* 主循环 */
    while (1) {
        uint32_t now = HAL_GetTick();

        /* 尝试解析串口数据 */
        FatiguePacket pkt = UART_Protocol_Parse();
        if (pkt.valid) {
            Feedback_SetLevel((FatigueLevel)pkt.level);
        }

        /* 定时更新 (闪烁、蜂鸣器节拍) */
        Feedback_Tick(now);
    }
}

/* ===== 系统时钟配置: 72MHz (HSE 8MHz + PLL x9) ===== */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLMUL = RCC_PLL_MUL9;
    HAL_RCC_OscConfig(&osc);

    RCC_ClkInitTypeDef clk = {0};
    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                  | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV2;   /* APB1 = 36MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;   /* APB2 = 72MHz */
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2);
}

/* ===== GPIO 初始化 ===== */
static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};

    /* PA0: TIM2_CH1 (WS2812B) — 复用推挽 */
    gpio.Pin = WS2812B_PIN;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(WS2812B_PORT, &gpio);

    /* PA6: TIM3_CH1 (蜂鸣器) — 复用推挽 */
    gpio.Pin = BUZZER_PIN;
    HAL_GPIO_Init(BUZZER_PORT, &gpio);
}

/* ===== DMA 初始化 ===== */
static void MX_DMA_Init(void)
{
    __HAL_RCC_DMA1_CLK_ENABLE();

    hdma_tim2_ch1.Instance = DMA1_Channel5;  /* TIM2_CH1 对应 DMA1_Channel5 */
    hdma_tim2_ch1.Init.Direction = DMA_MEMORY_TO_PERIPH;
    hdma_tim2_ch1.Init.PeriphInc = DMA_PINC_DISABLE;
    hdma_tim2_ch1.Init.MemInc = DMA_MINC_ENABLE;
    hdma_tim2_ch1.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
    hdma_tim2_ch1.Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
    hdma_tim2_ch1.Init.Mode = DMA_NORMAL;
    hdma_tim2_ch1.Init.Priority = DMA_PRIORITY_HIGH;
    HAL_DMA_Init(&hdma_tim2_ch1);

    __HAL_LINKDMA(&htim2, hdma[TIM_DMA_ID_CC1], hdma_tim2_ch1);

    HAL_NVIC_SetPriority(DMA1_Channel5_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(DMA1_Channel5_IRQn);
}

/* ===== TIM2: WS2812B PWM (800kHz, ARR=89) ===== */
static void MX_TIM2_Init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();

    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 0;              /* 72MHz 直接驱动 */
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 89;                /* 72MHz / 90 = 800kHz */
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim2);

    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_1);
}

/* ===== TIM3: 蜂鸣器 PWM (2kHz 默认频率) ===== */
static void MX_TIM3_Init(void)
{
    __HAL_RCC_TIM3_CLK_ENABLE();

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 71;             /* 72MHz / 72 = 1MHz */
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 499;               /* 1MHz / 500 = 2kHz */
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim3);

    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;                          /* 初始静音 */
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim3, &oc, TIM_CHANNEL_1);
}

/* ===== USART1: 115200, 8N1 ===== */
static void MX_USART1_UART_Init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();

    /* PA9 TX, PA10 RX */
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = GPIO_PIN_9;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = GPIO_PIN_10;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &gpio);

    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    HAL_UART_Init(&huart1);

    HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
}

/* ===== 中断处理 ===== */
void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

void DMA1_Channel5_IRQHandler(void)
{
    HAL_DMA_IRQHandler(&hdma_tim2_ch1);
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        extern uint8_t rx_byte;
        UART_Protocol_RxCallback(rx_byte);
    }
}

void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM2) {
        WS2812B_DMA_Callback();
    }
}

void Error_Handler(void)
{
    while (1) {}
}
