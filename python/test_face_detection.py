"""人脸检测调试脚本"""

import cv2
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import CONFIG
from capture.camera import Camera
from face.detector import FaceDetector


def test_face_detection():
    """测试人脸检测"""
    print("=" * 60)
    print("人脸检测调试")
    print("=" * 60)

    # 初始化
    print("\n[1] 初始化相机和检测器...")
    camera = Camera(CONFIG)
    detector = FaceDetector(CONFIG)
    print("✓ 初始化完成")

    # 统计
    total_frames = 0
    face_detected_frames = 0

    print("\n[2] 开始检测（按 'q' 退出）...")
    print("提示：")
    print("  - 绿色框 = 检测到人脸")
    print("  - 红色文字 = 未检测到人脸")
    print("  - 蓝色框 = ROI区域（额头）\n")

    while True:
        ret, frame = camera.read()
        if not ret:
            print("读取帧失败")
            break

        total_frames += 1

        # 人脸检测
        face_box = detector.detect(frame)

        if face_box is not None:
            face_detected_frames += 1
            x1, y1, x2, y2 = face_box

            # 绘制人脸框（绿色）
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 绘制ROI区域（蓝色）
            face_w = x2 - x1
            face_h = y2 - y1
            roi_x1 = int(x1 + face_w * CONFIG["roi_x_start"])
            roi_y1 = int(y1 + face_h * CONFIG["roi_y_start"])
            roi_x2 = int(x1 + face_w * CONFIG["roi_x_end"])
            roi_y2 = int(y1 + face_h * CONFIG["roi_y_end"])
            cv2.rectangle(frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 0, 0), 2)

            # 显示信息
            cv2.putText(frame, "Face Detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Box: {x2-x1}x{y2-y1}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            # 未检测到人脸
            cv2.putText(frame, "No Face Detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 显示统计
        detection_rate = (face_detected_frames / total_frames * 100) if total_frames > 0 else 0
        cv2.putText(frame, f"Detection Rate: {detection_rate:.1f}%", (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow('Face Detection Test', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

    # 总结
    print("\n" + "=" * 60)
    print("检测统计")
    print("=" * 60)
    print(f"总帧数: {total_frames}")
    print(f"检测到人脸的帧数: {face_detected_frames}")
    print(f"检测率: {detection_rate:.1f}%")

    if detection_rate < 50:
        print("\n⚠ 检测率较低，可能的原因：")
        print("  1. 光照不足（检查850nm LED补光）")
        print("  2. 面部不在画面中央")
        print("  3. 距离太远或太近")
        print("  4. 人脸检测器配置不当")
    elif detection_rate < 80:
        print("\n⚠ 检测率一般，建议：")
        print("  1. 调整相机位置")
        print("  2. 增强补光")
    else:
        print("\n✓ 检测率良好！")


if __name__ == "__main__":
    test_face_detection()
