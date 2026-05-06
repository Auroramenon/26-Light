"""相机单独测试脚本 - 用于调试相机连接"""

import cv2
import numpy as np

def test_camera(camera_index=0):
    """测试相机是否正常工作"""
    print(f"尝试打开相机 {camera_index}...")

    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"❌ 无法打开相机 {camera_index}")
        print("\n可能的原因：")
        print("1. 相机未连接")
        print("2. 相机被其他程序占用")
        print("3. camera_index 不正确")
        print("\n尝试其他索引：")
        for i in range(5):
            test_cap = cv2.VideoCapture(i)
            if test_cap.isOpened():
                print(f"  ✓ 索引 {i} 可用")
                test_cap.release()
            else:
                print(f"  ✗ 索引 {i} 不可用")
        return False

    print(f"✓ 相机打开成功")

    # 获取相机属性
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"\n相机属性：")
    print(f"  分辨率: {int(width)}x{int(height)}")
    print(f"  帧率: {fps} FPS")

    # 采集几帧测试
    print(f"\n采集测试帧...")
    for i in range(10):
        ret, frame = cap.read()
        if not ret:
            print(f"  ❌ 第{i+1}帧采集失败")
            cap.release()
            return False

        # 分析图像
        mean_brightness = np.mean(frame)
        print(f"  第{i+1}帧: {frame.shape}, 平均亮度: {mean_brightness:.1f}")

        # 保存第一帧用于检查
        if i == 0:
            cv2.imwrite("test_frame.jpg", frame)
            print(f"  → 已保存为 test_frame.jpg")

    # 实时预览（按q退出）
    print(f"\n开始实时预览（按 'q' 退出）...")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("读取帧失败")
            break

        # 显示亮度信息
        mean_brightness = np.mean(frame)
        cv2.putText(frame, f"Brightness: {mean_brightness:.1f}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Camera Test', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    print("\n✓ 相机测试完成")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("相机连接测试")
    print("=" * 60)

    # 从config读取相机索引
    try:
        from config import CONFIG
        camera_index = CONFIG.get("camera_index", 0)
        print(f"使用配置文件中的相机索引: {camera_index}\n")
    except:
        camera_index = 0
        print(f"使用默认相机索引: {camera_index}\n")

    success = test_camera(camera_index)

    if success:
        print("\n✓ 相机工作正常！")
    else:
        print("\n❌ 相机测试失败，请检查硬件连接")
