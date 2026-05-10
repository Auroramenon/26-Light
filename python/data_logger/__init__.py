"""数据采集和可视化模块"""

from .recorder import DataRecorder

# 延迟导入可视化工具，避免在主程序中强制依赖pandas/matplotlib
def get_visualizer():
    from .visualizer import DataVisualizer
    return DataVisualizer

__all__ = ["DataRecorder", "get_visualizer"]
