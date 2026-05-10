"""数据可视化脚本 — 从记录的CSV文件生成图表

用法:
    python visualize_data.py test_data/20260510_143000_data.csv
    python visualize_data.py test_data/20260510_143000_data.csv --report
"""

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from data_logger.visualizer import DataVisualizer


def main():
    parser = argparse.ArgumentParser(description="数据可视化工具")
    parser.add_argument("csv_file", type=str, help="CSV数据文件路径")
    parser.add_argument("--report", action="store_true", help="生成文本报告")
    parser.add_argument("--output-prefix", type=str, default=None, help="输出文件名前缀")
    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.csv_file):
        print(f"错误: 文件不存在: {args.csv_file}")
        return 1

    try:
        # 创建可视化工具
        visualizer = DataVisualizer(args.csv_file)

        # 生成所有图表
        visualizer.plot_all(output_prefix=args.output_prefix)

        # 生成报告（可选）
        if args.report:
            visualizer.generate_report()

        print("\n[完成] 所有图表已生成")
        return 0

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
