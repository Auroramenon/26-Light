"""串口发送模块 — 通过 USB-to-TTL 向 STM32 发送疲劳等级"""

import serial
import threading
from comm.protocol import build_packet


class SerialSender:
    """串口发送器，非阻塞发送"""

    def __init__(self, config):
        self.enabled = config["serial_enabled"]
        self._port = None
        if self.enabled:
            try:
                self._port = serial.Serial(
                    port=config["serial_port"],
                    baudrate=config["serial_baud"],
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.1,
                )
                print(f"[串口] 已连接 {config['serial_port']} @ {config['serial_baud']}")
            except serial.SerialException as e:
                print(f"[串口] 连接失败: {e}，将以离线模式运行")
                self.enabled = False

    def send(self, level, hr):
        """发送疲劳等级和心率到 STM32"""
        if not self.enabled or self._port is None:
            return
        packet = build_packet(level, hr)
        try:
            self._port.write(packet)
        except serial.SerialException:
            pass

    def close(self):
        if self._port and self._port.is_open:
            self._port.close()

    def __del__(self):
        self.close()
