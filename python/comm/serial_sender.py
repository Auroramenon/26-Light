"""串口发送模块 — 通过 USB-to-TTL 向 STM32 发送疲劳等级"""

import serial
import time
from comm.protocol import build_packet


class SerialSender:
    """串口发送器，带节流与自动重连"""

    def __init__(self, config):
        self.enabled = config["serial_enabled"]
        self.port_name = config["serial_port"]
        self.baud = config["serial_baud"]
        self.reconnect_interval = config.get("serial_reconnect_interval_sec", 2.0)
        self.send_interval = config.get("serial_send_interval_sec", 0.5)
        self.max_failures = config.get("serial_max_failures", 5)

        self._port = None
        self._last_send_ts = 0.0
        self._last_reconnect_ts = 0.0
        self._failures = 0
        self._rate_limited_drops = 0
        self._state = "disabled" if not self.enabled else "disconnected"

        if self.enabled:
            self._connect(initial=True)

    def _connect(self, initial=False):
        """尝试建立串口连接。"""
        try:
            self._port = serial.Serial(
                port=self.port_name,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            )
            self._state = "ready"
            self._failures = 0
            msg = "已连接" if initial else "重连成功"
            print(f"[串口] {msg} {self.port_name} @ {self.baud}")
            return True
        except serial.SerialException as e:
            self._state = "disconnected"
            if initial:
                print(f"[串口] 初始连接失败: {e}，将尝试后台重连")
            return False

    def tick(self, now=None):
        """维护连接状态；建议在主循环中周期调用。"""
        if not self.enabled:
            return

        if self._port is not None and self._port.is_open:
            self._state = "ready"
            return

        if now is None:
            now = time.time()
        if now - self._last_reconnect_ts < self.reconnect_interval:
            return

        self._last_reconnect_ts = now
        self._connect(initial=False)

    def send(self, level, hr, now=None):
        """发送疲劳等级和心率到 STM32"""
        if not self.enabled:
            return False

        if now is None:
            now = time.time()

        self.tick(now)
        if self._port is None or not self._port.is_open:
            return False

        if now - self._last_send_ts < self.send_interval:
            self._rate_limited_drops += 1
            return False

        packet = build_packet(level, hr)
        try:
            self._port.write(packet)
            self._last_send_ts = now
            self._failures = 0
            self._state = "ready"
            return True
        except (serial.SerialException, OSError) as e:
            self._failures += 1
            self._state = "disconnected"
            print(f"[串口] 发送失败({self._failures}/{self.max_failures}): {e}")
            self._close_port()
            if self._failures >= self.max_failures:
                print("[串口] 连续失败过多，进入重连等待")
                self._last_reconnect_ts = now
            return False

    def status(self):
        return {
            "enabled": self.enabled,
            "state": self._state,
            "failures": self._failures,
            "rate_limited_drops": self._rate_limited_drops,
            "port": self.port_name,
            "baud": self.baud,
        }

    def _close_port(self):
        if self._port and self._port.is_open:
            self._port.close()
        self._port = None

    def close(self):
        self._close_port()

    def __del__(self):
        self.close()
