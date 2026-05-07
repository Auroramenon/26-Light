"""串口通信测试工具 - 独立测试串口连接和数据发送"""

import serial
import serial.tools.list_ports
import time
import sys

# 导入协议模块
try:
    from comm.protocol import build_packet
except ImportError:
    # 如果导入失败，手动实现
    def build_packet(level, hr):
        body = f"FL,{int(level)},{int(hr)}"
        checksum = 0
        for c in body:
            checksum ^= ord(c)
        return f"${body},{checksum:02X}\r\n".encode("ascii")


def list_ports():
    """列出所有可用串口"""
    print("\n" + "=" * 60)
    print("检测系统串口...")
    print("=" * 60)

    ports = serial.tools.list_ports.comports()

    if not ports:
        print("\n[错误] 未找到任何串口设备！")
        print("\n请检查:")
        print("  1. USB-to-TTL 模块是否已插入")
        print("  2. STM32 是否通过 USB 连接")
        print("  3. 驱动是否已安装")
        return None

    print(f"\n找到 {len(ports)} 个串口:\n")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device}")
        print(f"   描述: {port.description}")
        print(f"   硬件ID: {port.hwid}")
        print()

    return ports


def test_serial_connection(port_name, baudrate=115200):
    """测试串口连接"""
    print("\n" + "=" * 60)
    print(f"测试串口连接: {port_name} @ {baudrate}")
    print("=" * 60)

    try:
        # 尝试打开串口
        print(f"\n[1/4] 正在打开串口 {port_name}...")
        ser = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,
        )
        print(f"✓ 串口打开成功")

        # 检查串口状态
        print(f"\n[2/4] 检查串口状态...")
        print(f"  - 端口: {ser.port}")
        print(f"  - 波特率: {ser.baudrate}")
        print(f"  - 是否打开: {ser.is_open}")
        print(f"✓ 串口状态正常")

        # 发送测试数据
        print(f"\n[3/4] 发送测试数据包...")
        test_cases = [
            (0, 72, "正常状态 - 绿灯"),
            (1, 68, "轻度疲劳 - 黄灯"),
            (2, 78, "中度疲劳 - 橙灯"),
            (3, 85, "重度疲劳 - 红灯闪烁"),
        ]

        for level, hr, desc in test_cases:
            packet = build_packet(level, hr)
            print(f"\n  发送: Level={level}, HR={hr} ({desc})")
            print(f"  数据包: {packet.decode('ascii').strip()}")
            print(f"  十六进制: {packet.hex()}")

            ser.write(packet)
            print(f"  ✓ 发送成功")

            # 等待 STM32 响应
            time.sleep(2)

            # 尝试读取响应 (如果有)
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"  收到响应: {response}")

        print(f"\n✓ 所有测试数据包发送成功")

        # 关闭串口
        print(f"\n[4/4] 关闭串口...")
        ser.close()
        print(f"✓ 串口已关闭")

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n如果 STM32 已正确连接并烧录固件，你应该看到:")
        print("  - LED 灯带依次变色: 绿 → 黄 → 橙 → 红闪")
        print("  - 蜂鸣器依次响起: 静音 → 慢间歇 → 快间歇 → 持续")
        print("\n如果没有反应，请检查:")
        print("  1. STM32 固件是否已烧录")
        print("  2. TX/RX 线是否交叉连接 (TX→RX, RX→TX)")
        print("  3. GND 线是否连接")
        print("  4. LED 灯带和蜂鸣器是否正确连接")

        return True

    except serial.SerialException as e:
        print(f"\n✗ 串口连接失败: {e}")
        print("\n可能的原因:")
        print("  1. 串口号不正确")
        print("  2. 串口被其他程序占用")
        print("  3. 权限不足")
        print("  4. 设备已断开")
        return False

    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("STM32 疲劳检测系统 - 串口测试工具")
    print("=" * 60)

    # 列出可用串口
    ports = list_ports()

    if not ports:
        print("\n请连接硬件后重新运行此脚本。")
        return

    # 选择串口
    if len(ports) == 1:
        selected_port = ports[0].device
        print(f"\n自动选择唯一的串口: {selected_port}")
    else:
        print("\n请选择要测试的串口:")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device} - {port.description}")

        try:
            choice = input(f"\n请输入序号 (1-{len(ports)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(ports):
                selected_port = ports[idx].device
            else:
                print("无效的选择")
                return
        except (ValueError, KeyboardInterrupt):
            print("\n已取消")
            return

    # 测试串口
    success = test_serial_connection(selected_port)

    if success:
        print("\n✓ 串口测试通过！")
        print(f"\n你可以在 config.py 中设置:")
        print(f'  "serial_port": "{selected_port}",')
        print(f'  "serial_enabled": True,')
        print(f"\n然后运行主程序:")
        print(f'  python main.py --serial {selected_port}')
    else:
        print("\n✗ 串口测试失败，请检查硬件连接和驱动安装。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
