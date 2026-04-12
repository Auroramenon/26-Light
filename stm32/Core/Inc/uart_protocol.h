#ifndef __UART_PROTOCOL_H
#define __UART_PROTOCOL_H

#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* 环形缓冲区大小 */
#define UART_RX_BUF_SIZE  64

/* 解析结果 */
typedef struct {
    uint8_t  level;     /* 疲劳等级 0-3 */
    uint16_t hr;        /* 心率 BPM */
    bool     valid;     /* 是否解析成功 */
} FatiguePacket;

/* 初始化 UART 接收 */
void UART_Protocol_Init(UART_HandleTypeDef *huart);

/* 尝试从缓冲区解析一个数据包（非阻塞，主循环调用） */
FatiguePacket UART_Protocol_Parse(void);

/* UART 接收中断回调（内部使用） */
void UART_Protocol_RxCallback(uint8_t byte);

#endif /* __UART_PROTOCOL_H */
