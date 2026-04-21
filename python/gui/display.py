"""OpenCV 实时 GUI 显示叠加层"""

import cv2
import numpy as np
from fusion.fatigue_classifier import LEVEL_NAMES, LEVEL_COLORS_BGR


class Display:
    """在视频帧上叠加检测信息"""

    WINDOW_NAME = "Fatigue Warning System"

    def __init__(self, config):
        self.show_gui = config["show_gui"]
        self.show_bvp = config["show_bvp_plot"]
        if self.show_gui:
            cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)

    def render(self, frame, box=None, roi_coords=None, hr=0, level=0,
               fatigue_score=0.0, perclos=0.0, yawn_rate=0, bvp=None):
        """在帧上绘制所有信息并显示"""
        if not self.show_gui:
            return

        vis = frame.copy()

        # 人脸框
        if box is not None:
            color = LEVEL_COLORS_BGR.get(level, (200, 200, 200))
            cv2.rectangle(vis, (box[0], box[1]), (box[2], box[3]), color, 2)

        # ROI 区域
        if roi_coords is not None:
            cv2.rectangle(vis, (roi_coords[0], roi_coords[1]),
                          (roi_coords[2], roi_coords[3]), (255, 255, 0), 1)

        # 信息面板
        panel_y = 30
        info_lines = [
            f"HR: {hr:.0f} BPM",
            f"Level: {level} - {LEVEL_NAMES.get(level, '?')}",
            f"Score: {fatigue_score:.2f}",
            f"PERCLOS: {perclos:.2f}",
            f"Yawn: {yawn_rate}/min",
        ]
        for line in info_lines:
            color = LEVEL_COLORS_BGR.get(level, (200, 200, 200))
            cv2.putText(vis, line, (10, panel_y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2)
            panel_y += 25

        # BVP 波形（右下角小图）
        if self.show_bvp and bvp is not None and len(bvp) > 10:
            bvp_img = self._draw_bvp(bvp, width=200, height=60)
            h, w = vis.shape[:2]
            y1 = h - 70
            x1 = w - 210
            if y1 > 0 and x1 > 0:
                vis[y1:y1 + 60, x1:x1 + 200] = bvp_img

        cv2.imshow(self.WINDOW_NAME, vis)

    def _draw_bvp(self, bvp, width=200, height=60):
        """绘制 BVP 波形小图"""
        img = np.zeros((height, width, 3), dtype=np.uint8)
        bvp = np.array(bvp[-width:])
        if len(bvp) < 2:
            return img

        # 归一化到 [5, height-5]
        mn, mx = bvp.min(), bvp.max()
        if mx - mn < 1e-6:
            return img
        norm = (bvp - mn) / (mx - mn)
        ys = (height - 5 - norm * (height - 10)).astype(int)
        xs = np.linspace(0, width - 1, len(ys)).astype(int)

        pts = np.column_stack([xs, ys])
        cv2.polylines(img, [pts], False, (0, 255, 0), 1)
        return img

    def check_quit(self):
        """检查是否按下 q/ESC 退出"""
        if not self.show_gui:
            return False
        key = cv2.waitKey(1) & 0xFF
        return key == ord("q") or key == 27

    def close(self):
        cv2.destroyAllWindows()
