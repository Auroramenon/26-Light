"""测试脚本：依次切换 level 0→1→2→3→0，每级持续 5 秒
直接通过 SPI 驱动 30 个 WS2812B，无需烧录 STM32。

硬件准备：
  把灯带数据线从 STM32 拔下，接到 Rockchip SPI MOSI 引脚
  默认使用 /dev/spidev2.0（spi2），若不对改 SPI_BUS 为 5

启用 SPI 设备节点（首次运行前）：
  sudo modprobe spidev
  若 /dev/spidev* 仍不出现，需在设备树里把 spidev 绑到 spi2/spi5
"""

import sys
import time

NUM_LEDS = 30
DURATION = 5        # 每个等级持续秒数
SPI_BUS = 2         # spi2 → /dev/spidev2.0，改成 5 则用 spi5
SPI_DEVICE = 0
SPI_SPEED_HZ = 6_400_000  # 6.4 MHz：每个 WS2812B bit = 8 SPI bits

# 每级颜色 (R, G, B)
LEVEL_COLORS = {
    0: (0,   80,  0),    # 绿 — 正常
    1: (100, 80,  0),    # 黄 — 轻度
    2: (180, 30,  0),    # 橙 — 中度
    3: (200,  0,  0),    # 红 — 重度
}

# ── WS2812B SPI 编码 ──────────────────────────────────────────────
# 6.4 MHz → 每 SPI bit ≈ 156 ns
# BIT1 = 0xF8 (11111000): T1H=781ns ✓  T1L=469ns ✓
# BIT0 = 0xE0 (11100000): T0H=469ns ✓  T0L=781ns ✓
_BIT1 = 0xF8
_BIT0 = 0xE0

def _encode_byte(val):
    out = []
    for bit in range(7, -1, -1):
        out.append(_BIT1 if (val >> bit) & 1 else _BIT0)
    return out

def _build_frame(colors):
    """colors: list of (r,g,b), 长度 = NUM_LEDS"""
    data = []
    for r, g, b in colors:
        for ch in (g, r, b):          # WS2812B 是 GRB 顺序
            data.extend(_encode_byte(ch))
    data.extend([0x00] * 50)          # 复位：50 µs 低电平
    return data

# ── 主逻辑 ────────────────────────────────────────────────────────
def main():
    try:
        import spidev
    except ImportError:
        sys.exit("[错误] 请先安装 spidev：pip install spidev")

    spi = spidev.SpiDev()
    try:
        spi.open(SPI_BUS, SPI_DEVICE)
    except FileNotFoundError:
        sys.exit(
            f"[错误] 找不到 /dev/spidev{SPI_BUS}.{SPI_DEVICE}\n"
            "请先运行：sudo modprobe spidev\n"
            "若仍无节点，需要在设备树里将 spidev 绑定到对应的 spi 控制器"
        )

    spi.max_speed_hz = SPI_SPEED_HZ
    spi.mode = 0

    print(f"SPI /dev/spidev{SPI_BUS}.{SPI_DEVICE} @ {SPI_SPEED_HZ//1000} kHz，{NUM_LEDS} 个 LED")

    try:
        for level in [0, 1, 2, 3, 0]:
            color = LEVEL_COLORS[level]
            frame = _build_frame([color] * NUM_LEDS)
            print(f"\n>>> Level {level}  RGB{color}  ({DURATION}s)")
            deadline = time.time() + DURATION
            while time.time() < deadline:
                spi.xfer2(frame)
                time.sleep(0.05)
            print()
    finally:
        # 关灯
        spi.xfer2(_build_frame([(0, 0, 0)] * NUM_LEDS))
        spi.close()

    print("完成：level 0→1→2→3→0 全部结束，灯已关闭")

if __name__ == "__main__":
    main()
