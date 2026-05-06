# 测试指南

## 测试文件夹结构

```
tests/
├── test_camera_only.py      # 相机连接测试
├── test_face_detection.py   # 人脸检测测试
├── test_full_system.py      # 完整系统测试
├── test_hr_accuracy.py      # 心率准确性测试
├── test_nir_only.py         # NIR模式专用测试
├── test_nir_rppg.py         # NIR rPPG信号处理测试
├── test_rppg_debug.py       # rPPG调试测试
└── README.md               # 本文件
```

## 快速开始

### 环境准备
1. 确保Python环境已激活：`.\.venv\Scripts\activate`
2. 安装依赖：`pip install -r requirements.txt`
3. 准备硬件：
   - NIR相机（850nm）或普通摄像头
   - 串口设备（可选，用于发送数据）

### 运行快速启动脚本
```bash
python quick_start_nir.py
```
此脚本会自动检查配置、硬件连接，然后启动主程序。

## 详细测试步骤

### 1. 基础测试（无需硬件）
```bash
# 检查依赖
python -c "import cv2, numpy, scipy, mediapipe, serial, torch; print('依赖正常')"
```

### 2. 硬件测试

#### 相机测试
```bash
python tests/test_camera_only.py
```
- **用途**：验证相机连接和帧读取
- **预期**：显示相机属性、帧信息、实时预览（按'q'退出）
- **问题排查**：
  - MSMF警告：Windows相机驱动问题，通常不影响功能
  - 无法打开相机：检查索引（0,1,2...）或路径

#### 人脸检测测试
```bash
python tests/test_face_detection.py
```
- **用途**：测试人脸检测和跟踪
- **预期**：实时显示人脸框和ROI区域
- **问题排查**：
  - 未检测到人脸：确保人脸在镜头前，光线充足
  - 脚本bug：`detection_rate`变量错误，已知问题

### 3. 算法测试

#### NIR rPPG测试
```bash
python tests/test_nir_rppg.py
```
- **用途**：测试NIR rPPG信号提取和心率计算
- **预期**：采集10秒信号，显示BVP、心率、HRV
- **问题排查**：
  - 未检测到人脸：需要真实人脸输入
  - 信号质量差：检查NIR LED是否开启

#### 心率准确性测试
```bash
python tests/test_hr_accuracy.py
```
- **用途**：验证心率估计准确性
- **预期**：比较估计心率与基准值
- **注意**：可能需要准备基准数据

#### 完整系统测试
```bash
python tests/test_full_system.py
```
- **用途**：测试所有模块集成
- **预期**：实时显示心率、PERCLOS、打哈欠、疲劳等级等指标
- **适合**：最终验证

### 4. 主程序测试

#### 基本运行
```bash
python main.py --no-gui --no-serial
```
- **用途**：运行完整系统，无界面，无串口
- **预期**：控制台输出状态信息

#### 完整运行
```bash
python main.py --camera 0 --serial COM3
```
- **用途**：完整疲劳检测系统
- **参数**：
  - `--camera 1`：指定相机索引
  - `--serial COM5`：指定串口
  - `--no-gui`：禁用界面
  - `--no-serial`：禁用串口

## 预期输出示例

### 正常运行输出
```
[系统] 正在初始化...
[系统] 初始化完成，开始运行 (按 q 退出)
[配置] 相机=0 方法=NIR_ADV 人脸=HC 串口=COM3
[状态] level=0 score=0.14 hr=75 HRV=OK(ok) 串口=正常 fail=0 drop=0
```

### 警告和错误
- `[警告] rPPG-Toolbox不可用`：RGB模式不可用，但NIR正常
- `[警告] MediaPipe初始化失败，禁用行为检测`：行为检测被禁用，系统仍可运行
- `[系统] 相机读取失败`：检查相机连接

## 故障排除

### 常见问题
1. **MediaPipe版本问题**
   - 现象：初始化失败
   - 解决：系统会自动降级功能，继续运行

2. **相机问题**
   - 现象：无法读取帧
   - 解决：检查相机索引，尝试不同值

3. **人脸检测失败**
   - 现象：无检测结果
   - 解决：调整光线、距离、角度

4. **串口问题**
   - 现象：连接失败
   - 解决：检查端口号，或使用`--no-serial`

### 性能优化
- 降低分辨率：修改`config.py`中的`camera_width/height`
- 调整检测间隔：修改`face_rescan_interval`

## 测试覆盖

- ✅ 相机捕获
- ✅ 人脸检测（Haar Cascade / YOLO5Face）
- ✅ ROI提取
- ✅ NIR rPPG信号处理
- ✅ 心率估计
- ✅ HRV分析
- ✅ 疲劳分类
- ⚠️ 行为检测（MediaPipe兼容性问题）
- ✅ 串口通信
- ✅ GUI显示

## 注意事项

1. 测试时确保人脸在相机视野内
2. NIR模式需要850nm LED补光灯
3. 串口测试需要连接外部设备
4. 部分测试脚本可能有已知bug，但不影响核心功能

如有问题，请检查控制台输出并参考上述排查步骤。