"""ILI9341 2.8寸 SPI 屏驱动（Orange Pi 5 Max / RK3588）

DC/RESET 通过 python-periphery 直接操作 /dev/gpiochipN 字符设备，
不依赖 RPi.GPIO（在 RK3588 上不可用）。

本板接线（wiringOP 实测）：
    MOSI Pin19 / SCLK Pin23 / CS0 Pin24  -> SPI0 (/dev/spidev0.0)
    DC   Pin22 = GPIO1_B0 -> /dev/gpiochip1 line 8
    RST  Pin13 = GPIO1_A1 -> /dev/gpiochip1 line 1
"""
from luma.core.interface.serial import spi
from luma.lcd.device import ili9341
from luma.core.render import canvas
from PIL import ImageFont
from periphery import GPIO
import os

LEVEL_COLORS = {
    0: (0, 200, 0),
    1: (255, 200, 0),
    2: (255, 100, 0),
    3: (255, 50, 50),
}

LEVEL_NAMES = {
    0: "NORMAL",
    1: "MILD",
    2: "MODERATE",
    3: "SEVERE",
}


class _NoopBacklight:
    """背光硬接 3.3V，不受程序控制：提供一个空操作对象绕过 luma 的 RPi.GPIO 背光初始化。"""
    def __call__(self, on=True):
        pass


class _PeripheryGPIO:
    """luma 兼容的 GPIO 后端，基于 /dev/gpiochip 字符设备。

    luma 把 ``pin`` 当作引脚编号传入；这里约定 pin = 同一 gpiochip 上的 line 偏移。
    """
    LOW = 0
    HIGH = 1
    OUT = "out"
    IN = "in"

    def __init__(self, chip="/dev/gpiochip1"):
        self._chip = chip
        self._lines = {}

    def setup(self, pin, direction):
        if pin not in self._lines:
            self._lines[pin] = GPIO(self._chip, pin, "out")

    def output(self, pin, value):
        self._lines[pin].write(bool(value))

    def input(self, pin):
        return self._lines[pin].read()

    def cleanup(self, pins=None):
        if pins is None:
            pins = list(self._lines)
        elif isinstance(pins, int):
            pins = [pins]
        for p in pins:
            line = self._lines.pop(p, None)
            if line is not None:
                line.close()


class OLEDScreen:
    def __init__(self, chip="/dev/gpiochip1", dc_line=8, rst_line=1,
                 port=0, device=0, bus_speed_hz=16000000, rotate=0):
        gpio = _PeripheryGPIO(chip)
        serial_interface = spi(
            gpio=gpio,
            port=port,
            device=device,
            bus_speed_hz=bus_speed_hz,
            gpio_DC=dc_line,
            gpio_RST=rst_line,
            reset_hold_time=0.1,
            reset_release_time=0.15,
        )
        self.device = ili9341(serial_interface, width=320, height=240,
                              rotate=rotate, backlight=_NoopBacklight())
        # 背光硬接 3.3V 常亮：luma 退出时默认发 DISPLAYOFF，会让面板停止驱动像素
        # 而背光仍亮 → 白屏。persist=True 跳过退出时的 hide()/clear()，
        # 最终画面由我们在 finally 中显式调用的 clear()（填黑）决定。
        self.device.persist = True

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(font_path):
            self.font_large = ImageFont.truetype(font_path, 32)
            self.font_medium = ImageFont.truetype(font_path, 22)
            self.font_small = ImageFont.truetype(font_path, 16)
        else:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def update(self, level: int, hr: float, score: float,
               perclos: float = 0.0, yawn_rate: float = 0.0):
        color = LEVEL_COLORS.get(level, (255, 255, 255))
        name = LEVEL_NAMES.get(level, "UNKNOWN")

        with canvas(self.device) as draw:
            draw.rectangle((0, 0, 320, 60), fill=color)
            draw.text((20, 12), f"LEVEL {level}", font=self.font_large, fill="black")
            draw.text((160, 22), name, font=self.font_medium, fill="black")

            y = 80
            draw.text((20, y),       f"HR     : {int(hr):3d} BPM",      font=self.font_medium, fill="white")
            draw.text((20, y + 35),  f"Score  : {score:.2f}",            font=self.font_medium, fill="white")
            draw.text((20, y + 70),  f"PERCLOS: {perclos * 100:5.1f} %", font=self.font_medium, fill="white")
            draw.text((20, y + 105), f"Yawn   : {yawn_rate:4.1f} /min",  font=self.font_medium, fill="white")

            draw.rectangle((0, 220, 320, 240), fill=(40, 40, 40))
            draw.text((10, 222), "Fatigue Monitor v1.0", font=self.font_small, fill="gray")

    def show_boot_screen(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, fill="black")
            draw.text((40, 80),  "Fatigue System",     font=self.font_large,  fill="cyan")
            draw.text((90, 130), "Booting...",          font=self.font_medium, fill="white")
            draw.text((30, 200), "Orange Pi + ILI9341", font=self.font_small,  fill="gray")

    def clear(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, fill="black")
