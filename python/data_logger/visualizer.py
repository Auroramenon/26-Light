"""数据可视化工具 — 从记录的数据生成图表"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np


class DataVisualizer:
    """数据可视化工具

    功能：
    1. 读取CSV数据文件
    2. 生成时间序列图表
    3. 生成统计分析图表
    4. 保存图表为PNG文件
    """

    def __init__(self, csv_path):
        """初始化可视化工具

        Args:
            csv_path: CSV数据文件路径
        """
        self.csv_path = csv_path
        self.df = None
        self.output_dir = os.path.dirname(csv_path)

        # 设置中文字体（Linux 使用 Noto CJK JP，Windows 使用 SimHei/微软雅黑）
        plt.rcParams['font.sans-serif'] = [
            'Noto Sans CJK JP', 'Noto Serif CJK JP',
            'Noto Sans CJK SC', 'WenQuanYi Micro Hei',
            'SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans'
        ]
        plt.rcParams['axes.unicode_minus'] = False

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载CSV数据"""
        try:
            self.df = pd.read_csv(self.csv_path)
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            print(f"[可视化] 已加载数据: {len(self.df)} 条记录")
        except Exception as e:
            print(f"[可视化] 加载数据失败: {e}")
            raise

    def plot_all(self, output_prefix=None):
        """生成所有图表

        Args:
            output_prefix: 输出文件名前缀（默认使用CSV文件名）
        """
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(self.csv_path))[0]

        print("[可视化] 开始生成图表...")

        # 1. 心率和HRV时间序列
        self.plot_hr_hrv(output_prefix)

        # 2. 行为特征时间序列
        self.plot_behavior(output_prefix)

        # 3. 疲劳评分和等级
        self.plot_fatigue(output_prefix)

        # 4. 风险分布
        self.plot_risks(output_prefix)

        # 5. 综合仪表板
        self.plot_dashboard(output_prefix)

        # 6. 统计摘要
        self.plot_statistics(output_prefix)

        print(f"[可视化] 图表已保存到: {self.output_dir}")

    def plot_hr_hrv(self, prefix):
        """绘制心率和HRV时间序列"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle('心率和HRV时间序列', fontsize=16, fontweight='bold')

        # 心率
        ax = axes[0]
        ax.plot(self.df['elapsed_time'], self.df['hr'], 'b-', linewidth=1.5, label='心率')
        ax.set_ylabel('心率 (BPM)', fontsize=12)
        ax.set_title('心率变化', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # HRV RMSSD 和 SDNN
        ax = axes[1]
        valid_mask = self.df['hrv_valid'] == True
        ax.plot(self.df.loc[valid_mask, 'elapsed_time'],
                self.df.loc[valid_mask, 'hrv_rmssd'],
                'g-', linewidth=1.5, label='RMSSD', alpha=0.8)
        ax.plot(self.df.loc[valid_mask, 'elapsed_time'],
                self.df.loc[valid_mask, 'hrv_sdnn'],
                'orange', linewidth=1.5, label='SDNN', alpha=0.8)
        ax.set_ylabel('HRV (ms)', fontsize=12)
        ax.set_title('HRV时域指标', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # HRV LF/HF
        ax = axes[2]
        ax.plot(self.df.loc[valid_mask, 'elapsed_time'],
                self.df.loc[valid_mask, 'hrv_lf_hf'],
                'purple', linewidth=1.5, label='LF/HF')
        ax.set_xlabel('时间 (秒)', fontsize=12)
        ax.set_ylabel('LF/HF比值', fontsize=12)
        ax.set_title('HRV频域指标', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, f"{prefix}_hr_hrv.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - 已生成: {output_path}")

    def plot_behavior(self, prefix):
        """绘制行为特征时间序列"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle('行为特征时间序列', fontsize=16, fontweight='bold')

        # PERCLOS
        ax = axes[0]
        ax.plot(self.df['elapsed_time'], self.df['perclos'], 'r-', linewidth=1.5)
        ax.axhline(y=0.12, color='orange', linestyle='--', alpha=0.5, label='低风险阈值')
        ax.axhline(y=0.25, color='red', linestyle='--', alpha=0.5, label='高风险阈值')
        ax.set_ylabel('PERCLOS', fontsize=12)
        ax.set_title('眼睛闭合比例 (PERCLOS)', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 哈欠率
        ax = axes[1]
        ax.plot(self.df['elapsed_time'], self.df['yawn_rate'], 'orange', linewidth=1.5)
        ax.axhline(y=0.15, color='orange', linestyle='--', alpha=0.5, label='低风险阈值')
        ax.axhline(y=0.8, color='red', linestyle='--', alpha=0.5, label='高风险阈值')
        ax.set_ylabel('哈欠率 (次/分)', fontsize=12)
        ax.set_title('哈欠频率', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 头部俯仰角
        ax = axes[2]
        ax.plot(self.df['elapsed_time'], self.df['head_pitch'], 'purple', linewidth=1.5)
        ax.axhline(y=12, color='orange', linestyle='--', alpha=0.5, label='低风险阈值')
        ax.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='高风险阈值')
        ax.axhline(y=-12, color='orange', linestyle='--', alpha=0.5)
        ax.axhline(y=-30, color='red', linestyle='--', alpha=0.5)
        ax.set_xlabel('时间 (秒)', fontsize=12)
        ax.set_ylabel('俯仰角 (度)', fontsize=12)
        ax.set_title('头部姿态', fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, f"{prefix}_behavior.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - 已生成: {output_path}")

    def plot_fatigue(self, prefix):
        """绘制疲劳评分和等级"""
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        fig.suptitle('疲劳评估', fontsize=16, fontweight='bold')

        # 疲劳评分
        ax = axes[0]
        ax.plot(self.df['elapsed_time'], self.df['fatigue_score'], 'b-', linewidth=2)
        ax.axhline(y=0.28, color='yellow', linestyle='--', alpha=0.5, label='轻度疲劳')
        ax.axhline(y=0.48, color='orange', linestyle='--', alpha=0.5, label='中度疲劳')
        ax.axhline(y=0.68, color='red', linestyle='--', alpha=0.5, label='重度疲劳')
        ax.set_ylabel('疲劳评分', fontsize=12)
        ax.set_title('综合疲劳评分', fontsize=13)
        ax.set_ylim([0, 1])
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 疲劳等级
        ax = axes[1]
        colors = ['green', 'yellow', 'orange', 'red']
        for level in range(4):
            mask = self.df['fatigue_level'] == level
            if mask.any():
                ax.scatter(self.df.loc[mask, 'elapsed_time'],
                          self.df.loc[mask, 'fatigue_level'],
                          c=colors[level], s=10, alpha=0.6,
                          label=f'Level {level}')
        ax.set_xlabel('时间 (秒)', fontsize=12)
        ax.set_ylabel('疲劳等级', fontsize=12)
        ax.set_title('疲劳等级变化', fontsize=13)
        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels(['正常', '轻度', '中度', '重度'])
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, f"{prefix}_fatigue.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - 已生成: {output_path}")

    def plot_risks(self, prefix):
        """为每类风险单独生成一张图（共4张）"""
        risks = [
            ('risk_hrv',     'HRV风险',    'g'),
            ('risk_perclos', 'PERCLOS风险', 'r'),
            ('risk_yawn',    '哈欠风险',    'orange'),
            ('risk_head',    '头姿风险',    'purple'),
        ]
        suffixes = ['risk_hrv', 'risk_perclos', 'risk_yawn', 'risk_head']

        for (col, title, color), suffix in zip(risks, suffixes):
            fig, ax = plt.subplots(figsize=(14, 5))
            fig.suptitle(title, fontsize=16, fontweight='bold')

            ax.plot(self.df['elapsed_time'], self.df[col],
                    color=color, linewidth=1.5)
            ax.set_xlabel('时间 (秒)', fontsize=12)
            ax.set_ylabel('风险分 (0-1)', fontsize=12)
            ax.set_ylim([0, 1])
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            output_path = os.path.join(self.output_dir, f"{prefix}_{suffix}.png")
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  - 已生成: {output_path}")

    def plot_dashboard(self, prefix):
        """绘制综合仪表板"""
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle('综合仪表板', fontsize=18, fontweight='bold')

        # 创建网格布局
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

        # 1. 心率
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(self.df['elapsed_time'], self.df['hr'], 'b-', linewidth=1.5)
        ax1.set_ylabel('心率 (BPM)')
        ax1.set_title('心率')
        ax1.grid(True, alpha=0.3)

        # 2. PERCLOS
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.plot(self.df['elapsed_time'], self.df['perclos'], 'r-', linewidth=1.5)
        ax2.set_ylabel('PERCLOS')
        ax2.set_title('眼睛闭合比例')
        ax2.grid(True, alpha=0.3)

        # 3. HRV RMSSD
        ax3 = fig.add_subplot(gs[1, 0])
        valid_mask = self.df['hrv_valid'] == True
        ax3.plot(self.df.loc[valid_mask, 'elapsed_time'],
                self.df.loc[valid_mask, 'hrv_rmssd'], 'g-', linewidth=1.5)
        ax3.set_ylabel('RMSSD (ms)')
        ax3.set_title('HRV RMSSD')
        ax3.grid(True, alpha=0.3)

        # 4. 哈欠率
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.plot(self.df['elapsed_time'], self.df['yawn_rate'], 'orange', linewidth=1.5)
        ax4.set_ylabel('哈欠率 (次/分)')
        ax4.set_title('哈欠频率')
        ax4.grid(True, alpha=0.3)

        # 5. 疲劳评分
        ax5 = fig.add_subplot(gs[2, :])
        ax5.plot(self.df['elapsed_time'], self.df['fatigue_score'], 'b-', linewidth=2)
        ax5.axhline(y=0.28, color='yellow', linestyle='--', alpha=0.5)
        ax5.axhline(y=0.48, color='orange', linestyle='--', alpha=0.5)
        ax5.axhline(y=0.68, color='red', linestyle='--', alpha=0.5)
        ax5.set_xlabel('时间 (秒)')
        ax5.set_ylabel('疲劳评分')
        ax5.set_title('综合疲劳评分')
        ax5.set_ylim([0, 1])
        ax5.grid(True, alpha=0.3)

        output_path = os.path.join(self.output_dir, f"{prefix}_dashboard.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - 已生成: {output_path}")

    def plot_statistics(self, prefix):
        """绘制统计摘要"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('统计摘要', fontsize=16, fontweight='bold')

        # 1. 疲劳等级分布
        ax = axes[0, 0]
        level_counts = self.df['fatigue_level'].value_counts().sort_index()
        colors_bar = ['green', 'yellow', 'orange', 'red']
        ax.bar(level_counts.index, level_counts.values,
               color=[colors_bar[int(i)] for i in level_counts.index], alpha=0.7)
        ax.set_xlabel('疲劳等级')
        ax.set_ylabel('记录数')
        ax.set_title('疲劳等级分布')
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(['正常', '轻度', '中度', '重度'])
        ax.grid(True, alpha=0.3, axis='y')

        # 2. 心率分布
        ax = axes[0, 1]
        hr_valid = self.df[self.df['hr'] > 0]['hr']
        ax.hist(hr_valid, bins=30, color='blue', alpha=0.7, edgecolor='black')
        ax.set_xlabel('心率 (BPM)')
        ax.set_ylabel('频数')
        ax.set_title(f'心率分布 (均值: {hr_valid.mean():.1f} BPM)')
        ax.grid(True, alpha=0.3, axis='y')

        # 3. PERCLOS分布
        ax = axes[1, 0]
        ax.hist(self.df['perclos'], bins=30, color='red', alpha=0.7, edgecolor='black')
        ax.axvline(x=0.12, color='orange', linestyle='--', linewidth=2, label='低风险')
        ax.axvline(x=0.25, color='red', linestyle='--', linewidth=2, label='高风险')
        ax.set_xlabel('PERCLOS')
        ax.set_ylabel('频数')
        ax.set_title(f'PERCLOS分布 (均值: {self.df["perclos"].mean():.3f})')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 4. 风险分对比
        ax = axes[1, 1]
        risk_means = [
            self.df['risk_hrv'].mean(),
            self.df['risk_perclos'].mean(),
            self.df['risk_yawn'].mean(),
            self.df['risk_head'].mean()
        ]
        risk_labels = ['HRV', 'PERCLOS', '哈欠', '头姿']
        colors_risk = ['green', 'red', 'orange', 'purple']
        ax.bar(risk_labels, risk_means, color=colors_risk, alpha=0.7)
        ax.set_ylabel('平均风险分')
        ax.set_title('各路平均风险分对比')
        ax.set_ylim([0, 1])
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, f"{prefix}_statistics.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - 已生成: {output_path}")

    def generate_report(self, output_path=None):
        """生成文本报告"""
        if output_path is None:
            output_path = os.path.join(self.output_dir,
                                      f"{os.path.splitext(os.path.basename(self.csv_path))[0]}_report.txt")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("疲劳检测测试报告\n")
            f.write("=" * 60 + "\n\n")

            # 基本信息
            f.write(f"数据文件: {self.csv_path}\n")
            f.write(f"记录数: {len(self.df)}\n")
            f.write(f"测试时长: {self.df['elapsed_time'].max():.1f} 秒\n\n")

            # 心率统计
            hr_valid = self.df[self.df['hr'] > 0]['hr']
            f.write("心率统计:\n")
            f.write(f"  平均值: {hr_valid.mean():.1f} BPM\n")
            f.write(f"  标准差: {hr_valid.std():.1f} BPM\n")
            f.write(f"  最小值: {hr_valid.min():.1f} BPM\n")
            f.write(f"  最大值: {hr_valid.max():.1f} BPM\n\n")

            # HRV统计
            hrv_valid = self.df[self.df['hrv_valid'] == True]
            if len(hrv_valid) > 0:
                f.write("HRV统计:\n")
                f.write(f"  RMSSD平均: {hrv_valid['hrv_rmssd'].mean():.2f} ms\n")
                f.write(f"  SDNN平均: {hrv_valid['hrv_sdnn'].mean():.2f} ms\n")
                f.write(f"  LF/HF平均: {hrv_valid['hrv_lf_hf'].mean():.3f}\n\n")

            # 行为特征统计
            f.write("行为特征统计:\n")
            f.write(f"  PERCLOS平均: {self.df['perclos'].mean():.3f}\n")
            f.write(f"  哈欠率平均: {self.df['yawn_rate'].mean():.2f} 次/分\n")
            f.write(f"  头部俯仰角平均: {self.df['head_pitch'].mean():.2f} 度\n\n")

            # 疲劳等级分布
            level_counts = self.df['fatigue_level'].value_counts().sort_index()
            level_names = ['正常', '轻度疲劳', '中度疲劳', '重度疲劳']
            f.write("疲劳等级分布:\n")
            for level, count in level_counts.items():
                percentage = count / len(self.df) * 100
                f.write(f"  {level_names[level]}: {count} 次 ({percentage:.1f}%)\n")
            f.write("\n")

            # 风险分统计
            f.write("风险分统计:\n")
            f.write(f"  HRV风险平均: {self.df['risk_hrv'].mean():.3f}\n")
            f.write(f"  PERCLOS风险平均: {self.df['risk_perclos'].mean():.3f}\n")
            f.write(f"  哈欠风险平均: {self.df['risk_yawn'].mean():.3f}\n")
            f.write(f"  头姿风险平均: {self.df['risk_head'].mean():.3f}\n\n")

            # 疲劳评分统计
            f.write("疲劳评分统计:\n")
            f.write(f"  平均值: {self.df['fatigue_score'].mean():.3f}\n")
            f.write(f"  标准差: {self.df['fatigue_score'].std():.3f}\n")
            f.write(f"  最小值: {self.df['fatigue_score'].min():.3f}\n")
            f.write(f"  最大值: {self.df['fatigue_score'].max():.3f}\n\n")

            f.write("=" * 60 + "\n")

        print(f"[可视化] 报告已生成: {output_path}")
        return output_path
