#ifndef __MAIN_H
#define __MAIN_H

#include "stm32f1xx_hal.h"

/* 外设句柄声明 */
extern UART_HandleTypeDef huart1;
extern TIM_HandleTypeDef htim2;   /* WS2812B PWM+DMA */
extern TIM_HandleTypeDef htim3;   /* 蜂鸣器 PWM */
extern DMA_HandleTypeDef hdma_tim2_ch1;

/* 系统时钟 */
void SystemClock_Config(void);
void Error_Handler(void);

/* GPIO 引脚定义 */
#define WS2812B_PIN       GPIO_PIN_0   /* PA0 - TIM2_CH1 */
#define WS2812B_PORT      GPIOA
#define BUZZER_PIN        GPIO_PIN_6   /* PA6 - TIM3_CH1 */
#define BUZZER_PORT       GPIOA

#endif /* __MAIN_H */
