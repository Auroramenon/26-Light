"""MediaPipe兼容层 - 支持新旧版本API

新版(0.10+): mediapipe.tasks.python.vision
旧版(0.8-0.9): mediapipe.solutions.face_mesh
"""

import sys

try:
    # 尝试新版API
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    _MEDIAPIPE_VERSION = "new"
    print("[MediaPipe] 使用新版API (0.10+)")
except (ImportError, AttributeError):
    # 回退到旧版API
    try:
        import mediapipe as mp
        _MEDIAPIPE_VERSION = "old"
        print("[MediaPipe] 使用旧版API (0.8-0.9)")
    except ImportError:
        print("[错误] MediaPipe未安装")
        sys.exit(1)


class FaceMeshWrapper:
    """MediaPipe Face Mesh包装器，兼容新旧API"""

    def __init__(self, max_num_faces=1, refine_landmarks=True,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):

        if _MEDIAPIPE_VERSION == "old":
            # 旧版API
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        else:
            # 新版API - 使用FaceLandmarker
            print("[警告] 新版MediaPipe (0.10+) 的Face Mesh API已改变")
            print("[提示] 建议降级到0.9版本: pip install mediapipe==0.9.3.0")
            print("[提示] 或者禁用行为检测功能")
            raise NotImplementedError(
                "新版MediaPipe (0.10+) 需要不同的API。\n"
                "请降级: pip install mediapipe==0.9.3.0"
            )

    def process(self, image):
        """处理图像，返回landmarks"""
        return self.face_mesh.process(image)

    def close(self):
        """关闭资源"""
        if hasattr(self.face_mesh, 'close'):
            self.face_mesh.close()


def get_face_mesh(**kwargs):
    """获取Face Mesh实例"""
    return FaceMeshWrapper(**kwargs)
