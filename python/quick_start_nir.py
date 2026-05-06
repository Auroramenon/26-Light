"""快速启动脚本 - NIR模式

快速启动夜间疲劳检测系统（NIR模式）

使用方法：
    python quick_start_nir.py

功能：
1. 自动检测配置
2. 验证硬件连接
3. 启动主程序

作者：26-Light项目组
"""

import sys
import os
import subprocess

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG


def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 70)
    print(" " * 15 + "NIR-rPPG 夜间疲劳检测系统")
    print(" " * 20 + "26-Light 项目组")
    print("=" * 70)


def check_config():
    """检查配置"""
    print("\n[1/4] 检查配置...")

    checks = [
        ("NIR相机模式", CONFIG.get("is_nir_camera", False)),
        ("rPPG方法", CONFIG.get("rppg_method", "").startswith("NIR")),
        ("HRV简化模式", CONFIG.get("nir_hrv_mode") == "simplified"),
    ]

    all_ok = True
    for name, status in checks:
        symbol = "[OK]" if status else "[X]"
        print(f"  {symbol} {name}: {status}")
        if not status:
            all_ok = False

    if not all_ok:
        print("\n  [!] 配置不完整，但可以继续运行")
        print("  建议检查 config.py 中的 NIR 相关配置")

    print("\n  配置摘要：")
    print(f"    - 相机: {CONFIG['camera_width']}x{CONFIG['camera_height']} @ {CONFIG['camera_fps']} FPS")
    print(f"    - rPPG: {CONFIG['rppg_method']}")
    print(f"    - 信号窗口: {CONFIG['signal_window_sec']}秒")
    print(f"    - HRV模式: {CONFIG.get('nir_hrv_mode', 'simplified')}")
    print(f"    - 权重: HRV={CONFIG['w_hrv']}, PERCLOS={CONFIG['w_perclos']}, "
          f"Yawn={CONFIG['w_yawn']}, Head={CONFIG['w_head']}")

    return True


def check_hardware():
    """检查硬件连接"""
    print("\n[2/4] 检查硬件连接...")

    # 检查相机
    print("  检查相机...")
    try:
        import cv2
        cap = cv2.VideoCapture(CONFIG["camera_index"])
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"    [OK] 相机连接正常")
                print(f"      实际分辨率: {frame.shape[1]}x{frame.shape[0]}")
                print(f"      平均亮度: {frame.mean():.1f}")
                if frame.mean() < 20:
                    print(f"      [!] 图像较暗，请确认850nm LED补光灯已打开")
            else:
                print(f"    [X] 相机无法读取帧")
                return False
            cap.release()
        else:
            print(f"    [X] 无法打开相机 (索引: {CONFIG['camera_index']})")
            print(f"      请检查相机连接或尝试修改 camera_index")
            return False
    except Exception as e:
        print(f"    [X] 相机检查失败: {e}")
        return False

    # 检查串口
    if CONFIG.get("serial_enabled", True):
        print("  检查串口...")
        try:
            import serial
            ser = serial.Serial(
                CONFIG["serial_port"],
                CONFIG["serial_baud"],
                timeout=1
            )
            print(f"    [OK] 串口连接正常 ({CONFIG['serial_port']})")
            ser.close()
        except Exception as e:
            print(f"    [!] 串口连接失败: {e}")
            print(f"      系统将在无串口模式下运行")

    return True


def run_quick_test():
    """运行快速测试"""
    print("\n[3/4] 运行快速测试...")
    print("  测试相机采集和人脸检测（5秒）...")

    try:
        import cv2
        from face.detector import FaceDetector

        cap = cv2.VideoCapture(CONFIG["camera_index"])
        detector = FaceDetector(CONFIG)

        face_detected = False
        for i in range(int(CONFIG["camera_fps"] * 5)):  # 5秒
            ret, frame = cap.read()
            if not ret:
                continue

            face_box = detector.detect(frame)
            if face_box is not None:
                face_detected = True
                break

        cap.release()

        if face_detected:
            print("    [OK] 人脸检测正常")
        else:
            print("    [!] 未检测到人脸")
            print("      请确保面部在相机视野内")

        return True

    except Exception as e:
        print(f"    [X] 快速测试失败: {e}")
        return False


def start_main_program():
    """启动主程序"""
    print("\n[4/4] 启动主程序...")

    # 构建命令
    cmd = ["python", "main.py"]

    # 添加串口参数
    if CONFIG.get("serial_enabled", True):
        cmd.extend(["--serial", CONFIG["serial_port"]])
    else:
        cmd.append("--no-serial")

    print(f"  命令: {' '.join(cmd)}")
    print("\n" + "=" * 70)
    print("系统启动中...")
    print("按 Ctrl+C 退出")
    print("=" * 70 + "\n")

    try:
        subprocess.run(cmd, cwd=os.path.dirname(__file__))
    except KeyboardInterrupt:
        print("\n\n系统已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        return False

    return True


def main():
    """主流程"""
    print_banner()

    # 检查配置
    if not check_config():
        print("\n配置检查失败，退出")
        return False

    # 检查硬件
    if not check_hardware():
        print("\n硬件检查失败，退出")
        response = input("\n是否仍要继续启动？(y/N): ")
        if response.lower() != 'y':
            return False

    # 快速测试
    if not run_quick_test():
        print("\n快速测试失败")
        response = input("\n是否仍要继续启动？(y/N): ")
        if response.lower() != 'y':
            return False

    # 启动主程序
    return start_main_program()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
