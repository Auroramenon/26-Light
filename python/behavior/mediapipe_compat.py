"""MediaPipe兼容层 - 支持新旧版本API

新版(0.10+): mediapipe.tasks.python.vision
旧版(0.8-0.9): mediapipe.solutions.face_mesh
"""

import sys
import numpy as np
from collections import namedtuple
import os
import urllib.request

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

        self.version = _MEDIAPIPE_VERSION

        if _MEDIAPIPE_VERSION == "old":
            # 旧版API
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        else:
            # 新版API - 使用FaceLandmarker (IMAGE模式，同步处理)
            print("[MediaPipe] 初始化新版FaceLandmarker...")
            
            # 下载模型文件到本地缓存
            model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "mediapipe")
            os.makedirs(cache_dir, exist_ok=True)
            model_path = os.path.join(cache_dir, "face_landmarker.task")
            
            if not os.path.exists(model_path):
                print(f"[MediaPipe] 下载模型文件到 {model_path}...")
                try:
                    urllib.request.urlretrieve(model_url, model_path)
                    print("[MediaPipe] 模型下载完成")
                except Exception as e:
                    print(f"[MediaPipe] 模型下载失败: {e}")
                    raise
            else:
                print(f"[MediaPipe] 使用缓存模型: {model_path}")
            
            base_options = python.BaseOptions(model_asset_path=model_path)
            
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,  # IMAGE模式，无需回调
                num_faces=max_num_faces,
                min_face_detection_confidence=min_detection_confidence,
                min_face_presence_confidence=min_tracking_confidence,
                min_tracking_confidence=min_tracking_confidence,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False
            )
            
            self.face_mesh = vision.FaceLandmarker.create_from_options(options)

    def process(self, image):
        """处理图像，返回landmarks（兼容旧版格式）"""
        if self.version == "old":
            # 旧版直接返回
            return self.face_mesh.process(image)
        else:
            # 新版API - 转换为旧版格式
            try:
                # 新版返回FaceLandmarkerResult
                # 需要先确保输入格式正确
                if not isinstance(image, mp.Image):
                    # 如果是numpy数组，转换为Image
                    if isinstance(image, np.ndarray):
                        # 确保是RGB格式
                        if len(image.shape) == 3 and image.shape[2] == 3:
                            mp_image = mp.Image(mp.ImageFormat.SRGB, image)
                        else:
                            raise ValueError(f"Image shape {image.shape} not supported")
                    else:
                        mp_image = image
                else:
                    mp_image = image

                result = self.face_mesh.detect(mp_image)

                # 转换为旧版格式以兼容现有代码
                if result.face_landmarks:
                    FaceMeshResult = namedtuple('FaceMeshResult', ['multi_face_landmarks'])

                    multi_face_landmarks = []
                    for face_landmarks in result.face_landmarks:
                        # 创建兼容旧版的landmark列表
                        landmarks = []
                        for landmark in face_landmarks:
                            # 创建兼容的landmark对象
                            Landmark = namedtuple('Landmark', ['x', 'y', 'z'])
                            landmark_obj = Landmark(
                                x=landmark.x,
                                y=landmark.y,
                                z=landmark.z if hasattr(landmark, 'z') else 0.0
                            )
                            landmarks.append(landmark_obj)
                        
                        # 创建FaceLandmarks包装
                        FaceLandmarks = namedtuple('FaceLandmarks', ['landmark'])
                        multi_face_landmarks.append(
                            FaceLandmarks(landmark=landmarks)
                        )

                    return FaceMeshResult(multi_face_landmarks=multi_face_landmarks)
                else:
                    # 无检测结果
                    FaceMeshResult = namedtuple('FaceMeshResult', ['multi_face_landmarks'])
                    return FaceMeshResult(multi_face_landmarks=None)
            except Exception as e:
                print(f"[MediaPipe] 检测失败: {e}")
                FaceMeshResult = namedtuple('FaceMeshResult', ['multi_face_landmarks'])
                return FaceMeshResult(multi_face_landmarks=None)

    def close(self):
        """关闭资源"""
        if hasattr(self.face_mesh, 'close'):
            self.face_mesh.close()


def get_face_mesh(**kwargs):
    """获取Face Mesh实例"""
    return FaceMeshWrapper(**kwargs)
