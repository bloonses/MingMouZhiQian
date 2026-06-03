import unittest
import cv2
import numpy as np
from face_quality import FaceQualityAssessment, QualityScore


class TestFaceQuality(unittest.TestCase):
    """人脸质量评估模块测试"""

    def setUp(self):
        """测试前准备"""
        self.assessor = FaceQualityAssessment()

    def create_high_quality_face(self, size=200):
        """创建高质量人脸图像（高对比度、清晰）"""
        img = np.zeros((size, size, 3), dtype=np.uint8)
        
        # 绘制人脸轮廓（确保所有参数为整数）
        axes = (size//3, int(size/2.5))
        cv2.ellipse(img, (size//2, size//2), axes, 0, 0, 360, (255, 200, 180), -1)
        
        # 添加清晰的五官
        cv2.circle(img, (size//2 - size//6, size//2 - size//8), size//15, (0, 0, 0), -1)
        cv2.circle(img, (size//2 + size//6, size//2 - size//8), size//15, (0, 0, 0), -1)
        cv2.circle(img, (size//2 - size//6, size//2 - size//8), size//30, (255, 255, 255), -1)
        cv2.circle(img, (size//2 + size//6, size//2 - size//8), size//30, (255, 255, 255), -1)
        
        # 鼻子和嘴巴
        cv2.line(img, (size//2, size//2 - size//10), (size//2, size//2 + size//10), (200, 150, 130), 3)
        mouth_axes = (size//8, size//15)
        cv2.ellipse(img, (size//2, size//2 + size//4), mouth_axes, 0, 0, 180, (200, 100, 100), 3)
        
        # 添加纹理和噪声增强细节
        noise = np.random.randint(0, 30, (size, size, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return img

    def create_blurry_face(self, size=200):
        """创建模糊的人脸图像"""
        img = self.create_high_quality_face(size)
        # 应用更强的高斯模糊
        img = cv2.GaussianBlur(img, (51, 51), 0)
        img = cv2.GaussianBlur(img, (51, 51), 0)
        return img

    def create_medium_quality_face(self, size=200):
        """创建中等质量图像"""
        img = self.create_high_quality_face(size)
        # 轻微模糊
        img = cv2.GaussianBlur(img, (7, 7), 0)
        return img

    def test_TR2_1_score_range(self):
        """TR-2.1: 质量分数范围正确（0-1）"""
        high_quality = self.create_high_quality_face()
        blurry = self.create_blurry_face()
        
        score_high = self.assessor.assess(high_quality)
        score_blurry = self.assessor.assess(blurry)
        
        # 验证所有分数在 0-1 范围内
        self.assertGreaterEqual(score_high.overall, 0.0)
        self.assertLessEqual(score_high.overall, 1.0)
        self.assertGreaterEqual(score_high.sharpness, 0.0)
        self.assertLessEqual(score_high.sharpness, 1.0)
        self.assertGreaterEqual(score_high.brightness, 0.0)
        self.assertLessEqual(score_high.brightness, 1.0)
        self.assertGreaterEqual(score_high.pose, 0.0)
        self.assertLessEqual(score_high.pose, 1.0)
        
        self.assertGreaterEqual(score_blurry.overall, 0.0)
        self.assertLessEqual(score_blurry.overall, 1.0)

    def test_TR2_2_low_quality_score(self):
        """TR-2.2: 模糊/低质量图像分数 < 0.3"""
        blurry = self.create_blurry_face()
        score = self.assessor.assess(blurry)
        
        # 模糊图像的整体分数应该 < 0.3
        self.assertLess(score.overall, 0.3)
        # 清晰度分数也应该很低
        self.assertLess(score.sharpness, 0.3)

    def test_TR2_3_high_quality_score(self):
        """TR-2.3: 高质量图像分数 > 0.8"""
        high_quality = self.create_high_quality_face()
        score = self.assessor.assess(high_quality)
        
        # 高质量图像的整体分数应该 > 0.8
        self.assertGreater(score.overall, 0.8)
        # 清晰度分数也应该较高
        self.assertGreater(score.sharpness, 0.6)

    def test_individual_assessments(self):
        """测试各个分项评估函数"""
        img = self.create_high_quality_face()
        
        sharpness = self.assessor.assess_sharpness(img)
        brightness = self.assessor.assess_brightness(img)
        pose = self.assessor.assess_pose()
        
        self.assertGreaterEqual(sharpness, 0.0)
        self.assertLessEqual(sharpness, 1.0)
        self.assertGreaterEqual(brightness, 0.0)
        self.assertLessEqual(brightness, 1.0)
        self.assertGreaterEqual(pose, 0.0)
        self.assertLessEqual(pose, 1.0)

    def test_quality_score_object(self):
        """测试 QualityScore 容器类"""
        score = QualityScore()
        self.assertEqual(score.sharpness, 0.0)
        self.assertEqual(score.brightness, 0.0)
        self.assertEqual(score.pose, 0.0)
        self.assertEqual(score.overall, 0.0)
        
        score.sharpness = 0.8
        score.brightness = 0.7
        score.pose = 0.9
        score.overall = 0.82
        self.assertEqual(score.sharpness, 0.8)
        self.assertEqual(score.brightness, 0.7)
        self.assertEqual(score.pose, 0.9)
        self.assertEqual(score.overall, 0.82)


if __name__ == '__main__':
    unittest.main()
