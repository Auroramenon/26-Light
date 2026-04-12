"""深度学习 rPPG 模型推理封装（可选模块）— TS-CAN / EfficientPhys"""

import sys
import os
import numpy as np
import cv2

_toolbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rPPG-Toolbox"))
if _toolbox_path not in sys.path:
    sys.path.insert(0, _toolbox_path)


class NeuralRPPG:
    """深度学习 rPPG 推理器，支持 EfficientPhys 和 TSCAN"""

    def __init__(self, config):
        import torch
        self.device = torch.device(config["device"])
        self.model_name = config["neural_model"]
        self.frame_depth = config["neural_frame_depth"]
        self.img_size = config["neural_img_size"]

        if self.model_name == "EfficientPhys":
            from neural_methods.model.EfficientPhys import EfficientPhys
            self.model = EfficientPhys(frame_depth=self.frame_depth, img_size=self.img_size)
        elif self.model_name == "TSCAN":
            from neural_methods.model.TS_CAN import TSCAN
            self.model = TSCAN(frame_depth=self.frame_depth, img_size=self.img_size)
        else:
            raise ValueError(f"不支持的模型: {self.model_name}")

        if config["neural_model_path"] and os.path.exists(config["neural_model_path"]):
            state = torch.load(config["neural_model_path"], map_location=self.device)
            self.model.load_state_dict(state)

        self.model.to(self.device).eval()

    def predict(self, roi_frames):
        """从 ROI 帧序列预测 BVP 信号

        Args:
            roi_frames: list of (H, W, 3) RGB 图像，长度 >= frame_depth + 1

        Returns:
            bvp: 1D numpy array
        """
        import torch

        frames = self._preprocess(roi_frames)
        with torch.no_grad():
            output = self.model(frames)
        return output.cpu().numpy().flatten()

    def _preprocess(self, roi_frames):
        """将 ROI 帧预处理为模型输入张量"""
        import torch

        processed = []
        for frame in roi_frames:
            resized = cv2.resize(frame, (self.img_size, self.img_size))
            resized = resized.astype(np.float32) / 255.0
            processed.append(resized)

        # (N, H, W, C) -> (N, C, H, W)
        arr = np.array(processed).transpose(0, 3, 1, 2)
        tensor = torch.from_numpy(arr).float().unsqueeze(0).to(self.device)
        return tensor
