# 数据采集和可视化功能使用说明

## 概述

本模块提供了实时数据采集和可视化功能，用于记录测试过程中的HR、HRV、PERCLOS、哈欠率、头姿等数据，并生成图表用于分析和报告。

## 目录结构

```
python/
├── data_logger/              # 数据记录模块
│   ├── __init__.py
│   ├── recorder.py          # 数据记录器
│   └── visualizer.py        # 数据可视化工具
├── visualize_data.py        # 可视化脚本
└── test_data/               # 数据输出目录（自动创建）
    ├── 20260510_143000_data.csv      # 数据文件
    ├── 20260510_143000_meta.json     # 元数据
    ├── 20260510_143000_hr_hrv.png    # 心率和HRV图表
    ├── 20260510_143000_behavior.png  # 行为特征图表
    ├── 20260510_143000_fatigue.png   # 疲劳评估图表
    ├── 20260510_143000_risks.png     # 风险分布图表
    ├── 20260510_143000_dashboard.png # 综合仪表板
    ├── 20260510_143000_statistics.png # 统计摘要
    └── 20260510_143000_report.txt    # 文本报告
```

## 使用方法

### 1. 启用数据记录

在运行主程序时添加 `--record` 参数：

```bash
# 基本用法（自动生成会话名称，默认1秒采样一次）
python main.py --record

# 指定会话名称
python main.py --record --session test_001

# 指定采样间隔（每2秒记录一次，减少数据量）
python main.py --record --sample-interval 2.0

# 指定输出目录
python main.py --record --output-dir my_data

# 完整示例
python main.py --camera 0 --record --session fatigue_test_20260510 --sample-interval 1.5 --output-dir test_data
```

**采样间隔说明**：
- 默认值：1.0秒（每秒记录一条数据）
- 推荐值：1.0-2.0秒（平衡数据量和精度）
- 长时间测试：可设置为2.0-5.0秒
- 采样策略：在每个间隔内，自动选择疲劳等级最高的数据记录，确保不遗漏重要信号

### 2. 数据记录说明

- **采样控制**：默认每1秒记录一条数据（可通过`--sample-interval`调整）
- **智能选择**：在采样间隔内，自动选择疲劳等级最高的数据，确保不遗漏重要的疲劳信号
- **实时保存**：数据实时写入CSV文件，不会因程序崩溃而丢失
- **状态显示**：每5秒在控制台显示记录状态
- **自动保存**：按 `q` 键退出时自动保存元数据

**记录的数据包括**：
  - 时间戳和经过时间
  - 心率 (HR)
  - HRV指标 (RMSSD, SDNN, pNN50, LF/HF)
  - 行为特征 (PERCLOS, 哈欠率, 头姿)
  - 疲劳评分和等级
  - 各路风险分

**数据量估算**：
  - 1秒采样：1小时约3600条记录，文件大小约500KB
  - 2秒采样：1小时约1800条记录，文件大小约250KB
  - 5秒采样：1小时约720条记录，文件大小约100KB

### 3. 生成图表

测试结束后，使用可视化脚本生成图表：

```bash
# 基本用法
python visualize_data.py test_data/20260510_143000_data.csv

# 同时生成文本报告
python visualize_data.py test_data/20260510_143000_data.csv --report

# 指定输出文件名前缀
python visualize_data.py test_data/20260510_143000_data.csv --output-prefix my_test
```

### 4. 生成的图表说明

#### 4.1 心率和HRV时间序列 (hr_hrv.png)
- 心率变化曲线
- HRV时域指标 (RMSSD, SDNN)
- HRV频域指标 (LF/HF)

#### 4.2 行为特征时间序列 (behavior.png)
- PERCLOS变化（含风险阈值线）
- 哈欠频率变化（含风险阈值线）
- 头部姿态变化（含风险阈值线）

#### 4.3 疲劳评估 (fatigue.png)
- 综合疲劳评分曲线（含等级阈值线）
- 疲劳等级变化散点图

#### 4.4 风险分布 (risks.png)
- HRV风险、PERCLOS风险、哈欠风险、头姿风险的时间序列对比

#### 4.5 综合仪表板 (dashboard.png)
- 6个子图的综合视图
- 快速了解整体测试情况

#### 4.6 统计摘要 (statistics.png)
- 疲劳等级分布柱状图
- 心率分布直方图
- PERCLOS分布直方图
- 各路平均风险分对比

#### 4.7 文本报告 (report.txt)
- 测试基本信息
- 各项指标的统计数据（均值、标准差、最大最小值）
- 疲劳等级分布百分比

## 数据格式说明

### CSV文件格式

CSV文件包含以下列：

| 列名 | 说明 | 单位 |
|------|------|------|
| timestamp | Unix时间戳 | 秒 |
| datetime | 日期时间字符串 | - |
| elapsed_time | 从开始到现在的时间 | 秒 |
| hr | 心率 | BPM |
| hrv_rmssd | HRV RMSSD | ms |
| hrv_sdnn | HRV SDNN | ms |
| hrv_pnn50 | HRV pNN50 | % |
| hrv_lf_hf | HRV LF/HF比值 | - |
| hrv_valid | HRV数据是否有效 | True/False |
| hrv_ibi_count | IBI数量 | - |
| perclos | PERCLOS | 0-1 |
| yawn_rate | 哈欠率 | 次/分 |
| head_pitch | 头部俯仰角度 | 度 |
| fatigue_score | 综合疲劳评分 | 0-1 |
| fatigue_level | 疲劳等级 | 0-3 |
| risk_hrv | HRV风险分 | 0-1 |
| risk_perclos | PERCLOS风险分 | 0-1 |
| risk_yawn | 哈欠风险分 | 0-1 |
| risk_head | 头姿风险分 | 0-1 |

### JSON元数据格式

```json
{
  "session_name": "20260510_143000",
  "start_time": "2026-05-10T14:30:00.123456",
  "end_time": "2026-05-10T14:45:00.123456",
  "total_records": 1500,
  "config": {
    "camera_fps": 30,
    "signal_window_sec": 10,
    "hrv_window_sec": 60,
    "rppg_method": "NIR_ADV",
    "face_det_backend": "HC",
    "fatigue_thresholds": [0.28, 0.48, 0.68],
    "upgrade_thresholds": [0.28, 0.48, 0.68],
    "downgrade_thresholds": [0.23, 0.42, 0.62],
    "weights": {
      "w_hrv": 0.18,
      "w_perclos": 0.45,
      "w_yawn": 0.22,
      "w_head": 0.15
    }
  }
}
```

## 注意事项

1. **采样间隔选择**：
   - 短时测试（<30分钟）：使用1.0秒，获得更详细的数据
   - 中等测试（30分钟-2小时）：使用1.5-2.0秒
   - 长时测试（>2小时）：使用3.0-5.0秒，减少数据量
   
2. **采样策略**：系统会在每个采样间隔内自动选择疲劳等级最高的数据，这样可以：
   - 确保不遗漏重要的疲劳信号
   - 记录最具代表性的状态
   - 大幅减少数据量（相比无限制记录）

3. **存储空间**：即使长时间测试，数据量也是可控的（1小时约100-500KB）

4. **图表生成**：生成图表需要matplotlib库，确保已安装：`pip install matplotlib pandas`

5. **中文显示**：如果图表中文显示异常，请确保系统安装了中文字体（SimHei或Microsoft YaHei）

## 示例工作流程

```bash
# 1. 启动测试并记录数据（每2秒采样一次，适合长时间测试）
python main.py --camera 0 --record --session morning_test --sample-interval 2.0

# 2. 测试过程中观察控制台输出
# [数据记录] 采样间隔: 2.0秒
# [记录] 会话: morning_test | 记录数: 150 | 时长: 300秒 | 状态: 记录中

# 3. 按 q 键退出测试

# 4. 生成图表和报告
python visualize_data.py test_data/morning_test_data.csv --report

# 5. 查看生成的图表和报告
# test_data/morning_test_*.png
# test_data/morning_test_report.txt
```

## 高级用法

### 在代码中使用数据记录器

```python
from data_logger.recorder import DataRecorder

# 创建记录器（每2秒采样一次）
recorder = DataRecorder(
    output_dir="my_data",
    session_name="test_001",
    sample_interval=2.0
)
recorder.set_config(CONFIG)

# 记录数据（可以频繁调用，系统会自动按采样间隔筛选）
recorder.record({
    "hr": 75.0,
    "hrv_features": {...},
    "perclos": 0.15,
    "yawn_rate": 0.3,
    "head_pitch": 5.0,
    "fatigue_score": 0.35,
    "fatigue_level": 1,
    "risks": {...}
})

# 暂停/恢复记录
recorder.pause()
recorder.resume()

# 关闭记录器
recorder.close()
```

### 在代码中使用可视化工具

```python
from data_logger.visualizer import DataVisualizer

# 创建可视化工具
viz = DataVisualizer("test_data/test_001_data.csv")

# 生成所有图表
viz.plot_all()

# 生成单个图表
viz.plot_hr_hrv("test_001")
viz.plot_behavior("test_001")
viz.plot_fatigue("test_001")

# 生成报告
viz.generate_report()
```

## 疲劳检测标准优化说明

本次更新优化了疲劳检测标准，主要改进包括：

### 1. 风险映射参数调整
- **PERCLOS阈值**：从 [0.15, 0.30] 调整为 [0.12, 0.25]，更早检测疲劳
- **哈欠率阈值**：从 [0.2, 1.0] 调整为 [0.15, 0.8]，更符合实际情况
- **头姿阈值**：从 [15°, 35°] 调整为 [12°, 30°]，更敏感

### 2. 融合权重优化
- **HRV权重**：从 0.20 降至 0.18（NIR模式下HRV准确度较低）
- **PERCLOS权重**：从 0.40 升至 0.45（最可靠的疲劳指标）
- **哈欠权重**：从 0.25 降至 0.22
- **头姿权重**：保持 0.15 不变

### 3. 疲劳等级阈值调整
- **升级阈值**：从 [0.30, 0.50, 0.70] 调整为 [0.28, 0.48, 0.68]
- **降级阈值**：从 [0.25, 0.45, 0.65] 调整为 [0.23, 0.42, 0.62]
- **持续时间**：从 5秒 缩短为 4秒，更快响应

### 4. Level 3多证据判定优化
- **PERCLOS阈值**：从 1.0 降至 0.85，更容易触发
- **HRV阈值**：从 0.7 升至 0.75，确保可靠性
- **哈欠阈值**：从 0.5 升至 0.6，避免误判
- **新增规则**：任意两路达到0.7即可判定为Level 3

这些优化使疲劳检测更加敏感和准确，能够更早地发现疲劳迹象。

## 技术支持

如有问题，请查看：
- 主程序文档：`README.md`
- 配置文件：`config.py`
- 数据记录器源码：`data_logger/recorder.py`
- 可视化工具源码：`data_logger/visualizer.py`
