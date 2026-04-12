/**
 * UART 串口协议解析 — USART1 中断接收 + 环形缓冲区
 *
 * 协议格式: $FL,<level>,<hr>,<checksum>\r\n
 * 示例: $FL,2,78,4A\r\n
 */

#include "uart_protocol.h"
#include <string.h>
#include <stdlib.h>

static UART_HandleTypeDef *proto_huart;
static uint8_t rx_byte;

/* 环形缓冲区 */
static uint8_t rx_buf[UART_RX_BUF_SIZE];
static volatile uint16_t rx_head = 0;
static volatile uint16_t rx_tail = 0;

/* 行缓冲 */
static char line_buf[UART_RX_BUF_SIZE];
static uint8_t line_pos = 0;

void UART_Protocol_Init(UART_HandleTypeDef *huart)
{
    proto_huart = huart;
    rx_head = 0;
    rx_tail = 0;
    line_pos = 0;
    /* 启动中断接收 */
    HAL_UART_Receive_IT(huart, &rx_byte, 1);
}

void UART_Protocol_RxCallback(uint8_t byte)
{
    uint16_t next = (rx_head + 1) % UART_RX_BUF_SIZE;
    if (next != rx_tail) {
        rx_buf[rx_head] = byte;
        rx_head = next;
    }
    /* 继续接收下一个字节 */
    HAL_UART_Receive_IT(proto_huart, &rx_byte, 1);
}

static uint8_t hex_val(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return 0xFF;
}

FatiguePacket UART_Protocol_Parse(void)
{
    FatiguePacket pkt = { .level = 0, .hr = 0, .valid = false };

    /* 从环形缓冲区读取字节，组装行 */
    while (rx_tail != rx_head) {
        uint8_t c = rx_buf[rx_tail];
        rx_tail = (rx_tail + 1) % UART_RX_BUF_SIZE;

        if (c == '\n') {
            line_buf[line_pos] = '\0';

            /* 解析: $FL,<level>,<hr>,<checksum> */
            if (line_pos >= 8 && line_buf[0] == '$' && line_buf[1] == 'F' && line_buf[2] == 'L') {
                /* 提取字段 */
                char *p = line_buf + 4;  /* 跳过 "$FL," */
                char *level_str = p;
                char *comma1 = strchr(p, ',');
                if (comma1) {
                    *comma1 = '\0';
                    char *hr_str = comma1 + 1;
                    char *comma2 = strchr(hr_str, ',');
                    if (comma2) {
                        *comma2 = '\0';
                        char *cksum_str = comma2 + 1;

                        /* 去掉可能的 \r */
                        char *cr = strchr(cksum_str, '\r');
                        if (cr) *cr = '\0';

                        /* 校验 XOR */
                        uint8_t calc_ck = 0;
                        for (char *s = line_buf + 1; s < comma2; s++) {
                            if (*s != '\0') calc_ck ^= (uint8_t)*s;
                        }

                        /* 重新计算: body = "FL,<level>,<hr>" */
                        calc_ck = 0;
                        /* 从 '$' 后到最后一个 ',' 前 */
                        char body[32];
                        int blen = snprintf(body, sizeof(body), "FL,%s,%s", level_str, hr_str);
                        for (int i = 0; i < blen; i++) {
                            calc_ck ^= (uint8_t)body[i];
                        }

                        uint8_t recv_ck = (hex_val(cksum_str[0]) << 4) | hex_val(cksum_str[1]);

                        if (calc_ck == recv_ck) {
                            pkt.level = (uint8_t)atoi(level_str);
                            pkt.hr = (uint16_t)atoi(hr_str);
                            if (pkt.level <= 3) {
                                pkt.valid = true;
                            }
                        }
                    }
                }
            }
            line_pos = 0;
            if (pkt.valid) return pkt;
        } else if (c != '\r') {
            if (line_pos < UART_RX_BUF_SIZE - 1) {
                line_buf[line_pos++] = (char)c;
            }
        }
    }

    return pkt;
}
