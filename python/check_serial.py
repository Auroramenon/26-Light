"""检查系统中可用的串口"""

import serial.tools.list_ports

print("=" * 60)
print("系统串口检查工具")
print("=" * 60)

ports = serial.tools.list_ports.comports()

if not ports:
    print("\n[警告] 未找到任何串口设备！")
    print("\n可能的原因:")
    print("  1. USB-to-TTL 模块未插入")
    print("  2. 驱动未安装 (CH340/CP2102/FT232)")
    print("  3. STM32 未通过 USB 连接")
    print("\n解决方法:")
    print("  1. 插入 USB-to-TTL 模块或 STM32")
    print("  2. 打开设备管理器检查是否识别")
    print("  3. 安装对应的驱动程序")
else:
    print(f"\n找到 {len(ports)} 个串口设备:\n")
    for i, port in enumerate(ports, 1):
        print(f"{i}. 端口: {port.device}")
        print(f"   描述: {port.description}")
        print(f"   硬件ID: {port.hwid}")
        print()

    print("=" * 60)
    print("配置建议:")
    print("=" * 60)

    # 找到最可能的串口
    likely_port = None
    for port in ports:
        desc_lower = port.description.lower()
        if any(keyword in desc_lower for keyword in ['ch340', 'cp210', 'ft232', 'usb-serial', 'stm32']):
            likely_port = port
            break

    if likely_port:
        print(f"\n推荐使用: {likely_port.device}")
        print(f"描述: {likely_port.description}")
        print(f"\n在 config.py 中设置:")
        print(f'  "serial_port": "{likely_port.device}",')
    else:
        print(f"\n请根据设备管理器中的信息选择正确的串口")
        print(f"通常是 COM3, COM4, COM5 等")

print("\n" + "=" * 60)
