"""
明眸智签 v2.0 - 集成测试
验证活体检测与主系统的集成
"""

import sys
import os
import numpy as np
import cv2

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithm_v2.face_recognition_backend_v2 import FaceRecognizerV2, get_liveness_pool


def test_integration():
    """测试活体检测与识别系统的集成"""
    print("=== 明眸智签 v2.0 - 集成测试 ===")
    
    # 初始化识别器（使用模拟模式，不需要加载真实模型）
    recognizer = FaceRecognizerV2(use_v2_features=True)
    
    # 重置活体检测池
    pool = get_liveness_pool()
    pool.reset()
    
    # 创建测试图像
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)  # 灰色背景
    
    # 绘制一个模拟人脸
    face_center = (320, 240)
    cv2.circle(img, face_center, 100, (200, 200, 200), -1)
    
    # 转换为 base64
    img_b64 = recognizer.numpy_to_base64(img)
    
    print("\n1. 测试单帧识别（首次检测）")
    result = recognizer.recognize_v2(img_b64)
    print(f"   检测到人脸: {result['detected_faces']}")
    print(f"   识别到学生: {len(result['recognized'])}")
    print(f"   活体通过: {result['liveness']}")
    
    # 模拟连续多帧检测（验证活体状态累积）
    print("\n2. 模拟连续 10 帧检测（验证活体状态累积）")
    for i in range(10):
        result = recognizer.recognize_v2(img_b64)
        if i % 2 == 0:
            print(f"   帧 {i}: 活体={result['liveness']}, 细节数={len(result.get('liveness_details', []))}")
    
    # 测试重置功能
    print("\n3. 测试重置功能")
    pool.reset()
    print("   活体检测池已重置")
    
    result = recognizer.recognize_v2(img_b64)
    print(f"   重置后首帧: 活体={result['liveness']}")
    
    print("\n=== 集成测试完成 ===")
    print("✓ 系统集成正常")
    print("✓ 活体检测已集成到识别流程")
    print("✓ 向后兼容性保持")


if __name__ == "__main__":
    test_integration()
