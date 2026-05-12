"""环境检测脚本 — 检查所有依赖是否正常

运行方法:
    python check_env.py
    python check_env.py --camera   # 同时打开摄像头预览
    python check_env.py --serial   # 同时测试串口连接
"""

import sys
import os
import argparse
import importlib

# ── 终端颜色 ───────────────────────────────────────────────────────────────
try:
    import shutil
    _has_color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
except Exception:
    _has_color = False

def _c(text, code):
    return f"\033[{code}m{text}\033[0m" if _has_color else text

OK   = lambda s: _c(f"[OK]    {s}", "32")
WARN = lambda s: _c(f"[WARN]  {s}", "33")
FAIL = lambda s: _c(f"[FAIL]  {s}", "31")
INFO = lambda s: _c(f"[INFO]  {s}", "36")
HEAD = lambda s: _c(s, "1")

pass_count = 0
fail_count = 0
warn_count = 0

def ok(msg):
    global pass_count
    pass_count += 1
    print(OK(msg))

def fail(msg):
    global fail_count
    fail_count += 1
    print(FAIL(msg))

def warn(msg):
    global warn_count
    warn_count += 1
    print(WARN(msg))

def info(msg):
    print(INFO(msg))

def section(title):
    print()
    print(HEAD("=" * 60))
    print(HEAD(f"  {title}"))
    print(HEAD("=" * 60))


# ══════════════════════════════════════════════════════════════════
# 1. Python 版本
# ══════════════════════════════════════════════════════════════════
section("1. Python 环境")

ver = sys.version_info
info(f"解释器路径: {sys.executable}")
info(f"Python 版本: {sys.version.split()[0]}")

if ver >= (3, 9):
    ok(f"Python {ver.major}.{ver.minor} — 版本满足要求 (>=3.9)")
else:
    fail(f"Python {ver.major}.{ver.minor} — 需要 3.9 及以上版本")


# ══════════════════════════════════════════════════════════════════
# 2. 核心依赖包
# ══════════════════════════════════════════════════════════════════
section("2. 核心依赖包")

REQUIRED_PACKAGES = [
    ("cv2",       "opencv-python",   "4.0.0"),
    ("numpy",     "numpy",           "1.20.0"),
    ("scipy",     "scipy",           "1.10.0"),
    ("mediapipe", "mediapipe",       "0.10.0"),
    ("serial",    "pyserial",        "3.5"),
]

OPTIONAL_PACKAGES = [
    ("torch",     "torch",           "2.1.0"),
]

def check_package(import_name, pip_name, min_ver, optional=False):
    try:
        mod = importlib.import_module(import_name)
        ver_str = getattr(mod, "__version__", "未知")
        # 版本比较（忽略后缀，只取数字部分）
        try:
            from packaging.version import Version
            meets = Version(ver_str) >= Version(min_ver)
        except Exception:
            try:
                parts = [int(x) for x in ver_str.split(".")[:3] if x.isdigit()]
                req   = [int(x) for x in min_ver.split(".")[:3]]
                meets = parts >= req
            except Exception:
                meets = True  # 无法比较时放行
        if meets:
            ok(f"{pip_name} {ver_str}")
        else:
            warn(f"{pip_name} {ver_str} — 建议升级到 >={min_ver}")
    except ImportError:
        if optional:
            warn(f"{pip_name} 未安装 (可选，安装命令: pip install {pip_name})")
        else:
            fail(f"{pip_name} 未安装 — 安装命令: pip install {pip_name}>={min_ver}")

for args in REQUIRED_PACKAGES:
    check_package(*args)

print()
info("可选依赖 (深度学习 rPPG):")
for args in OPTIONAL_PACKAGES:
    check_package(*args, optional=True)


# ══════════════════════════════════════════════════════════════════
# 3. 项目模块导入
# ══════════════════════════════════════════════════════════════════
section("3. 项目模块导入")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

PROJECT_MODULES = [
    ("config",                    "全局配置"),
    ("capture.camera",            "相机采集"),
    ("face.detector",             "人脸检测"),
    ("face.tracker",              "KLT跟踪"),
    ("face.roi",                  "ROI提取"),
    ("rppg.signal_buffer",        "信号缓冲"),
    ("rppg.unsupervised",         "rPPG无监督算法"),
    ("rppg.hr_estimator",         "心率估算"),
    ("rppg.hrv_analyzer",         "HRV分析"),
    ("rppg.nir_rppg",             "NIR rPPG"),
    ("rppg.nir_hrv",              "NIR HRV"),
    ("behavior.eye_detector",     "眼部检测 (PERCLOS)"),
    ("behavior.yawn_detector",    "哈欠检测"),
    ("behavior.head_pose",        "头姿估计"),
    ("behavior.mediapipe_compat", "MediaPipe兼容层"),
    ("fusion.feature_fusion",     "特征融合"),
    ("fusion.fatigue_classifier", "疲劳分类器"),
    ("comm.serial_sender",        "串口发送"),
    ("comm.protocol",             "通信协议"),
    ("gui.display",               "GUI显示"),
    ("data_logger.recorder",      "数据记录"),
]

for mod_name, desc in PROJECT_MODULES:
    try:
        importlib.import_module(mod_name)
        ok(f"{mod_name:<35} {desc}")
    except ImportError as e:
        fail(f"{mod_name:<35} {desc} — {e}")
    except Exception as e:
        warn(f"{mod_name:<35} {desc} — 导入异常: {e}")


# ══════════════════════════════════════════════════════════════════
# 4. 核心算法功能验证
# ══════════════════════════════════════════════════════════════════
section("4. 核心算法功能验证")

def test_numpy():
    import numpy as np
    a = np.random.randn(300)
    result = np.fft.rfft(a)
    assert result.shape[0] == 151
    ok("NumPy FFT 运算正常")

def test_scipy():
    from scipy.signal import butter, filtfilt
    import numpy as np
    b, a = butter(4, [0.7/15, 4.0/15], btype='band')
    sig = np.random.randn(300)
    filtered = filtfilt(b, a, sig)
    assert filtered.shape == sig.shape
    ok("SciPy 带通滤波器正常")

def test_rppg_buffer():
    from rppg.signal_buffer import SignalBuffer
    import numpy as np
    buf = SignalBuffer(fps=30, window_sec=10)
    dummy_roi = np.zeros((32, 32, 3), dtype=np.uint8)
    for _ in range(50):
        buf.append(dummy_roi)
    assert len(buf) == 50
    ok("SignalBuffer 读写正常")

def test_fatigue_classifier():
    from fusion.fatigue_classifier import FatigueClassifier
    from config import CONFIG
    clf = FatigueClassifier(CONFIG)
    result = clf.update(0.1)
    assert isinstance(result, int) and 0 <= result <= 3
    ok("FatigueClassifier 分类逻辑正常")

def test_protocol():
    from comm.protocol import build_packet
    frame = build_packet(level=1, hr=75)
    assert isinstance(frame, (bytes, bytearray)) and len(frame) > 0
    ok("通信协议帧构建正常")

for fn in [test_numpy, test_scipy, test_rppg_buffer, test_fatigue_classifier, test_protocol]:
    try:
        fn()
    except Exception as e:
        fail(f"{fn.__name__} — {e}")


# ══════════════════════════════════════════════════════════════════
# 5. MediaPipe 人脸网格
# ══════════════════════════════════════════════════════════════════
section("5. MediaPipe 人脸网格")

try:
    import mediapipe as mp
    import numpy as np
    import cv2

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    )
    # 用纯色图像做一次推理，验证模型可加载
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    _ = face_mesh.process(cv2.cvtColor(dummy, cv2.COLOR_BGR2RGB))
    face_mesh.close()
    ok("MediaPipe FaceMesh 模型加载并推理成功")
except Exception as e:
    fail(f"MediaPipe FaceMesh — {e}")


# ══════════════════════════════════════════════════════════════════
# 6. OpenCV 相机
# ══════════════════════════════════════════════════════════════════
section("6. 摄像头检测")

try:
    import cv2

    found = []
    for idx in range(6):
        cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            found.append((idx, w, h))
            cap.release()

    if found:
        for idx, w, h in found:
            marker = " <== config camera_index" if idx == 1 else ""
            ok(f"摄像头 index={idx}  分辨率 {w}x{h}{marker}")
    else:
        warn("未检测到任何摄像头 (index 0-5)")
        info("若相机已接入，请检查 USB 连接或驱动")

except Exception as e:
    fail(f"摄像头检测异常 — {e}")


# ══════════════════════════════════════════════════════════════════
# 7. 串口检测
# ══════════════════════════════════════════════════════════════════
section("7. 串口检测")

try:
    import serial.tools.list_ports
    from config import CONFIG

    ports = list(serial.tools.list_ports.comports())
    configured_port = CONFIG.get("serial_port", "COM3")

    if ports:
        ok(f"发现 {len(ports)} 个串口设备:")
        for p in ports:
            marker = " <== config serial_port" if p.device == configured_port else ""
            info(f"  {p.device}  {p.description}{marker}")
    else:
        warn("未发现串口设备 (STM32/USB-TTL 未连接?)")

    # 检查配置中的串口是否存在
    available_names = [p.device for p in ports]
    if configured_port in available_names:
        ok(f"配置串口 {configured_port} 可用")
    else:
        if CONFIG.get("serial_enabled", True):
            warn(f"配置串口 {configured_port} 不在已发现列表中")
            info(f"  若不使用串口，可在 config.py 中设置 \"serial_enabled\": False")
        else:
            info(f"串口已在 config.py 中禁用 (serial_enabled=False)")

except Exception as e:
    fail(f"串口检测异常 — {e}")


# ══════════════════════════════════════════════════════════════════
# 8. 可选：实时摄像头帧读取
# ══════════════════════════════════════════════════════════════════
def test_camera_live(camera_index):
    section("8. 实时摄像头帧读取 (--camera)")
    try:
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(camera_index, cv2.CAP_ANY)
        if not cap.isOpened():
            fail(f"无法打开摄像头 index={camera_index}")
            return

        ok(f"摄像头 index={camera_index} 已打开")
        info("按 'q' 退出预览窗口...")

        while True:
            ret, frame = cap.read()
            if not ret:
                warn("读帧失败")
                break
            cv2.putText(frame, "check_env.py: press Q to quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Camera Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        ok("摄像头帧读取正常，预览已关闭")
    except Exception as e:
        fail(f"摄像头帧读取 — {e}")


# ══════════════════════════════════════════════════════════════════
# 9. 可选：串口连接测试
# ══════════════════════════════════════════════════════════════════
def test_serial_connect():
    section("9. 串口连接测试 (--serial)")
    try:
        import serial
        from config import CONFIG

        port = CONFIG["serial_port"]
        baud = CONFIG["serial_baud"]
        info(f"尝试连接 {port} @ {baud}...")
        ser = serial.Serial(port, baud, timeout=2)
        if ser.is_open:
            ok(f"串口 {port} 连接成功")
            ser.close()
        else:
            fail(f"串口 {port} 打开失败")
    except serial.SerialException as e:
        fail(f"串口连接失败 — {e}")
    except Exception as e:
        fail(f"串口连接异常 — {e}")


# ══════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════
def summary(args):
    if args.camera:
        from config import CONFIG
        test_camera_live(CONFIG.get("camera_index", 1))
    if args.serial:
        test_serial_connect()

    section("检测结果汇总")
    total = pass_count + fail_count + warn_count
    print(OK(f"通过: {pass_count}/{total}"))
    if warn_count:
        print(WARN(f"警告: {warn_count}/{total}"))
    if fail_count:
        print(FAIL(f"失败: {fail_count}/{total}"))
        print()
        print(FAIL("环境存在问题，请根据上方 [FAIL] 信息修复后再运行主程序。"))
    elif warn_count:
        print()
        print(WARN("环境基本就绪，存在警告项，可酌情处理。"))
    else:
        print()
        print(OK("所有检测通过！环境就绪，可运行: python main.py"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="26-Light 环境检测脚本")
    parser.add_argument("--camera", action="store_true", help="打开摄像头预览 (需 GUI)")
    parser.add_argument("--serial", action="store_true", help="测试串口实际连接")
    args = parser.parse_args()
    summary(args)
