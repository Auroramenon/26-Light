"""小屏自检：验证 ILI9341 + periphery GPIO 链路。
需要 root： sudo /home/fd/miniforge3/bin/python3 test_oled.py
"""
import time
from display.oled_screen import OLEDScreen

print("[1] 初始化屏幕...")
oled = OLEDScreen()          # 使用 config 默认：gpiochip1, DC=8, RST=1, spidev0.0

print("[2] 开机画面 (3s)...")
oled.show_boot_screen()
time.sleep(3)

print("[3] 模拟等级 0 -> 3 ...")
for lvl in (0, 1, 2, 3):
    oled.update(level=lvl, hr=72 + lvl * 5, score=0.2 + lvl * 0.25,
                perclos=0.1 * lvl, yawn_rate=float(lvl))
    print(f"    LEVEL {lvl}")
    time.sleep(2)

print("[4] 清屏退出")
oled.clear()
print("[OK] 屏幕工作正常")
