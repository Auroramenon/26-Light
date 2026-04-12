"""串口通信协议定义"""


def build_packet(level, hr):
    """构建发送给 STM32 的数据包

    格式: $FL,<level>,<hr>,<checksum>\r\n
    checksum: 'FL,<level>,<hr>' 所有字符的 XOR，2位十六进制

    Args:
        level: 疲劳等级 0-3
        hr: 心率 BPM (int)

    Returns:
        bytes: 编码后的数据包
    """
    body = f"FL,{int(level)},{int(hr)}"
    checksum = 0
    for c in body:
        checksum ^= ord(c)
    return f"${body},{checksum:02X}\r\n".encode("ascii")


def parse_packet(data):
    """解析从 STM32 收到的应答包（可选）

    格式: $ACK,<level>\r\n

    Returns:
        level (int) 或 None
    """
    try:
        text = data.decode("ascii").strip()
        if text.startswith("$ACK,"):
            return int(text[5:])
    except (ValueError, UnicodeDecodeError):
        pass
    return None
