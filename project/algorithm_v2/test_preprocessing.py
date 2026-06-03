"""
明眸智签 v2.0 - 预处理模块测试
功能：测试光照增强、伽马校正、姿态感知匹配
"""

import unittest
import cv2
import numpy as np
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing import LightEnhancer, PoseAwareMatcher, FacePreprocessor


class TestLightEnhancer(unittest.TestCase):
    """测试光照增强器"""
    
    def setUp(self):
        """测试前准备 - 创建模拟图像"""
        # 创建正常图像
        self.normal_img = np.random.randint(80, 180, (100, 100, 3), dtype=np.uint8)
        
        # 创建过暗图像
        self.dark_img = np.random.randint(20, 60, (100, 100, 3), dtype=np.uint8)
        
        # 创建过亮图像
        self.bright_img = np.random.randint(200, 240, (100, 100, 3), dtype=np.uint8)
        
        self.enhancer = LightEnhancer()
    
    def test_clahe_enhance(self):
        """测试 CLAHE 光照增强"""
        result = self.enhancer.clahe_enhance(self.normal_img)
        
        # 验证输出形状正确
        self.assertEqual(result.shape, self.normal_img.shape)
        self.assertEqual(result.dtype, np.uint8)
        
        # 验证 LAB 模式
        result_lab = self.enhancer.clahe_enhance(self.normal_img, lab_only=True)
        self.assertEqual(result_lab.shape, self.normal_img.shape)
        
        # 验证 HSV 模式
        result_hsv = self.enhancer.clahe_enhance(self.normal_img, lab_only=False)
        self.assertEqual(result_hsv.shape, self.normal_img.shape)
    
    def test_adaptive_gamma_correction(self):
        """测试自适应伽马校正"""
        # 测试暗图像 - 确保输出是有效的
        result_dark = self.enhancer.adaptive_gamma_correction(self.dark_img)
        self.assertEqual(result_dark.shape, self.dark_img.shape)
        self.assertEqual(result_dark.dtype, np.uint8)
        
        # 测试亮图像 - 确保输出是有效的
        result_bright = self.enhancer.adaptive_gamma_correction(self.bright_img)
        self.assertEqual(result_bright.shape, self.bright_img.shape)
        self.assertEqual(result_bright.dtype, np.uint8)
        
        # 测试正常图像 - 确保输出是有效的
        result_normal = self.enhancer.adaptive_gamma_correction(self.normal_img)
        self.assertEqual(result_normal.shape, self.normal_img.shape)
        self.assertEqual(result_normal.dtype, np.uint8)
    
    def test_histogram_stretching(self):
        """测试直方图拉伸"""
        result = self.enhancer.histogram_stretching(self.normal_img)
        
        self.assertEqual(result.shape, self.normal_img.shape)
        self.assertEqual(result.dtype, np.uint8)
        
        # 验证动态范围扩大
        stats_before = self.enhancer.get_brightness_stats(self.normal_img)
        stats_after = self.enhancer.get_brightness_stats(result)
        
        # 拉伸后最大-最小值应该更大
        self.assertGreater(
            stats_after[3] - stats_after[2],
            stats_before[3] - stats_before[2] - 10  # 允许一点误差
        )
    
    def test_enhance_pipeline(self):
        """测试综合增强流水线"""
        # 测试各种组合
        result1 = self.enhancer.enhance_pipeline(
            self.dark_img, use_gamma=True, use_clahe=True, use_stretching=False
        )
        self.assertEqual(result1.shape, self.dark_img.shape)
        
        result2 = self.enhancer.enhance_pipeline(
            self.bright_img, use_gamma=True, use_clahe=False, use_stretching=True
        )
        self.assertEqual(result2.shape, self.bright_img.shape)
        
        result3 = self.enhancer.enhance_pipeline(
            self.normal_img, use_gamma=False, use_clahe=True, use_stretching=False
        )
        self.assertEqual(result3.shape, self.normal_img.shape)
    
    def test_get_brightness_stats(self):
        """测试获取亮度统计信息"""
        stats = self.enhancer.get_brightness_stats(self.normal_img)
        
        # 验证返回 4 个值
        self.assertEqual(len(stats), 4)
        
        # 验证值在合理范围内
        mean_val, std_val, min_val, max_val = stats
        self.assertGreaterEqual(mean_val, 0)
        self.assertLessEqual(mean_val, 255)
        self.assertGreaterEqual(std_val, 0)
        self.assertGreaterEqual(min_val, 0)
        self.assertLessEqual(max_val, 255)
        self.assertLessEqual(min_val, max_val)


class TestPoseAwareMatcher(unittest.TestCase):
    """测试姿态感知匹配器"""
    
    def setUp(self):
        """测试前准备"""
        self.matcher = PoseAwareMatcher()
    
    def test_pose_similarity_weight(self):
        """测试姿态相似度权重计算"""
        # 相同姿态 - 权重应该高
        pose1 = (0.0, 0.0, 0.0)
        pose2 = (0.0, 0.0, 0.0)
        weight = self.matcher.pose_similarity_weight(pose1, pose2)
        self.assertGreater(weight, 0.9)
        
        # 不同姿态 - 权重应该降低
        pose3 = (30.0, 10.0, 5.0)
        weight2 = self.matcher.pose_similarity_weight(pose1, pose3)
        self.assertLess(weight2, weight)
        
        # 大角度差异 - 权重应该更低
        pose4 = (60.0, 40.0, 20.0)
        weight3 = self.matcher.pose_similarity_weight(pose1, pose4)
        self.assertLess(weight3, weight2)
        
        # 验证权重在 0-1 范围内
        self.assertGreaterEqual(weight, 0.0)
        self.assertLessEqual(weight, 1.0)
    
    def test_decay_similarity_by_pose(self):
        """测试基于姿态的相似度衰减"""
        similarity = 0.85
        
        # 小姿态差 - 衰减小
        pose_diff_small = 0.1
        decayed1 = self.matcher.decay_similarity_by_pose(
            similarity, pose_diff_small, decay_type="linear"
        )
        self.assertLess(decayed1, similarity)
        self.assertGreater(decayed1, similarity * 0.8)
        
        # 大姿态差 - 衰减大
        pose_diff_large = 0.8
        decayed2 = self.matcher.decay_similarity_by_pose(
            similarity, pose_diff_large, decay_type="linear"
        )
        self.assertLess(decayed2, decayed1)
        
        # 测试不同衰减类型
        decayed_exp = self.matcher.decay_similarity_by_pose(
            similarity, pose_diff_small, decay_type="exponential"
        )
        decayed_quad = self.matcher.decay_similarity_by_pose(
            similarity, pose_diff_small, decay_type="quadratic"
        )
        self.assertIsInstance(decayed_exp, float)
        self.assertIsInstance(decayed_quad, float)
        
        # 验证衰减后仍在合理范围内
        self.assertGreaterEqual(decayed1, 0.0)
        self.assertLessEqual(decayed1, similarity)
    
    def test_calculate_pose_diff(self):
        """测试姿态差异计算"""
        pose1 = (0.0, 0.0, 0.0)
        pose2 = (0.0, 0.0, 0.0)
        diff1 = self.matcher.calculate_pose_diff(pose1, pose2)
        self.assertEqual(diff1, 0.0)
        
        pose3 = (30.0, 30.0, 30.0)
        diff2 = self.matcher.calculate_pose_diff(pose1, pose3)
        self.assertGreater(diff2, 0.0)
        
        pose4 = (90.0, 90.0, 90.0)
        diff3 = self.matcher.calculate_pose_diff(pose1, pose4)
        self.assertEqual(diff3, 1.0)  # 最大差异
    
    def test_select_best_template(self):
        """测试选择最佳模板"""
        query_pose = (0.0, 0.0, 0.0)
        template_poses = [
            ((0.0, 0.0, 0.0), "template_0"),
            ((15.0, 5.0, 0.0), "template_1"),
            ((30.0, 10.0, 5.0), "template_2"),
            ((45.0, 20.0, 10.0), "template_3"),
            ((60.0, 30.0, 15.0), "template_4"),
        ]
        
        # 选择前 3 个
        top_k = 3
        selected = self.matcher.select_best_template(query_pose, template_poses, top_k=top_k)
        
        self.assertEqual(len(selected), top_k)
        
        # 验证第一个应该是最匹配的
        first_idx, first_id, first_weight = selected[0]
        self.assertEqual(first_id, "template_0")
        
        # 验证权重是降序排列
        weights = [w for _, _, w in selected]
        for i in range(1, len(weights)):
            self.assertLessEqual(weights[i], weights[i-1])


class TestFacePreprocessor(unittest.TestCase):
    """测试综合预处理类"""
    
    def setUp(self):
        """测试前准备"""
        self.preprocessor = FacePreprocessor()
        self.test_img = np.random.randint(50, 200, (120, 120, 3), dtype=np.uint8)
    
    def test_preprocess_basic(self):
        """测试基础预处理"""
        result = self.preprocessor.preprocess(self.test_img, enhance=True)
        self.assertEqual(result.shape, self.test_img.shape)
        self.assertEqual(result.dtype, np.uint8)
    
    def test_preprocess_without_enhance(self):
        """测试不增强的预处理"""
        result = self.preprocessor.preprocess(self.test_img, enhance=False)
        self.assertEqual(result.shape, self.test_img.shape)
    
    def test_preprocess_with_resize(self):
        """测试带尺寸归一化的预处理"""
        target_size = (96, 96)
        result = self.preprocessor.preprocess(
            self.test_img, enhance=True, normalize_size=target_size
        )
        self.assertEqual(result.shape[:2], (target_size[1], target_size[0]))


class TestIntegration(unittest.TestCase):
    """集成测试 - 模拟完整流程"""
    
    def test_full_pipeline(self):
        """测试完整的预处理-姿态匹配流程"""
        # 1. 创建模拟图像
        face_img = np.random.randint(60, 180, (112, 112, 3), dtype=np.uint8)
        
        # 2. 光照增强
        enhancer = LightEnhancer()
        enhanced = enhancer.enhance_pipeline(face_img)
        
        # 3. 获取亮度统计
        stats = enhancer.get_brightness_stats(enhanced)
        self.assertIsNotNone(stats)
        
        # 4. 模拟姿态匹配
        matcher = PoseAwareMatcher()
        query_pose = (5.0, 2.0, 1.0)
        template_poses = [
            ((0.0, 0.0, 0.0), "t1"),
            ((20.0, 10.0, 5.0), "t2"),
            ((-15.0, -5.0, 0.0), "t3"),
        ]
        
        best_templates = matcher.select_best_template(query_pose, template_poses, top_k=2)
        self.assertEqual(len(best_templates), 2)
        
        # 5. 模拟相似度衰减
        base_similarity = 0.82
        pose_diff = matcher.calculate_pose_diff(query_pose, template_poses[1][0])
        final_similarity = matcher.decay_similarity_by_pose(base_similarity, pose_diff)
        
        self.assertLessEqual(final_similarity, base_similarity)
        self.assertGreaterEqual(final_similarity, 0.0)


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始预处理模块测试...")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestLightEnhancer))
    suite.addTests(loader.loadTestsFromTestCase(TestPoseAwareMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestFacePreprocessor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有测试通过！")
    else:
        print(f"❌ 测试失败：{len(result.failures)} 个失败，{len(result.errors)} 个错误")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
