"""
FAISS 索引模块测试
包含 TR-4.1 和 TR-4.2 验证
"""

import unittest
import numpy as np
import tempfile
import os
import time
import sys

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faiss_index import FaceVectorIndex, SearchResult, FAISS_AVAILABLE


class TestFaissIndex(unittest.TestCase):
    @unittest.skipIf(not FAISS_AVAILABLE, "FAISS 不可用，跳过测试")
    def setUp(self):
        """初始化测试"""
        self.dim = 512
        self.index = FaceVectorIndex(dim=self.dim)
    
    def test_add_and_search(self):
        """测试添加模板和基本搜索"""
        # 创建随机特征
        feature1 = np.random.rand(self.dim).astype('float32')
        feature2 = np.random.rand(self.dim).astype('float32')
        
        # 添加模板
        self.index.add_template("student_001", feature1, 0)
        self.index.add_template("student_002", feature2, 0)
        
        # 搜索
        results = self.index.search(feature1, k=2)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].student_id, "student_001")
        self.assertGreater(results[0].similarity, 0.0)
    
    def test_batch_add_and_batch_search(self):
        """测试批量添加和批量搜索"""
        n_samples = 10
        student_ids = [f"student_{i:03d}" for i in range(n_samples)]
        features = np.random.rand(n_samples, self.dim).astype('float32')
        
        # 批量添加
        self.index.add_templates_batch(student_ids, features)
        
        # 验证数量
        self.assertEqual(len(self.index), n_samples)
        self.assertEqual(self.index.get_student_count(), n_samples)
        
        # 批量搜索
        queries = features[:3]
        all_results = self.index.batch_search(queries, k=3)
        
        # 验证结果数量
        self.assertEqual(len(all_results), 3)
        for i, results in enumerate(all_results):
            self.assertEqual(results[0].student_id, student_ids[i])
    
    def test_remove_student(self):
        """测试移除学生"""
        # 添加学生
        feature1 = np.random.rand(self.dim).astype('float32')
        feature2 = np.random.rand(self.dim).astype('float32')
        self.index.add_template("student_001", feature1, 0)
        self.index.add_template("student_002", feature2, 0)
        
        # 移除学生
        self.index.remove_student("student_001")
        
        # 验证
        self.assertEqual(len(self.index), 1)
        self.assertEqual(self.index.get_student_count(), 1)
        
        # 搜索验证
        results = self.index.search(feature1, k=1)
        self.assertEqual(results[0].student_id, "student_002")
    
    def test_tr42_save_load(self):
        """TR-4.2 保存和加载功能测试"""
        # 添加一些数据
        n_samples = 50
        student_ids = [f"student_{i:03d}" for i in range(n_samples)]
        features = np.random.rand(n_samples, self.dim).astype('float32')
        self.index.add_templates_batch(student_ids, features)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='') as f:
            temp_path = f.name
        
        try:
            # 保存
            self.index.save(temp_path)
            
            # 加载
            loaded_index = FaceVectorIndex.load(temp_path)
            
            # 验证数据一致性
            self.assertEqual(len(loaded_index), n_samples)
            self.assertEqual(loaded_index.get_student_count(), n_samples)
            
            # 验证搜索结果一致
            query = features[0]
            results1 = self.index.search(query, k=5)
            results2 = loaded_index.search(query, k=5)
            
            self.assertEqual(len(results1), len(results2))
            for r1, r2 in zip(results1, results2):
                self.assertEqual(r1.student_id, r2.student_id)
                self.assertAlmostEqual(r1.similarity, r2.similarity, places=5)
        finally:
            # 清理
            if os.path.exists(temp_path + '.index'):
                os.remove(temp_path + '.index')
            if os.path.exists(temp_path + '.meta'):
                os.remove(temp_path + '.meta')
    
    def test_tr41_search_performance(self):
        """TR-4.1 500人库搜索性能测试（要求 <5ms）"""
        n_students = 500
        n_templates_per_student = 1
        total_templates = n_students * n_templates_per_student
        
        print(f"\nTR-4.1: 测试 {n_students} 人库（共 {total_templates} 个模板")
        
        # 生成测试数据
        student_ids = []
        features = np.random.rand(total_templates, self.dim).astype('float32')
        
        for i in range(n_students):
            student_ids.append(f"student_{i:03d}")
        
        # 批量添加
        self.index.add_templates_batch(student_ids, features)
        
        # 准备查询
        query = features[250]  # 中间的一个特征
        
        # 预热搜索
        for _ in range(10):
            _ = self.index.search(query, k=5)
        
        # 正式性能测试
        n_tests = 100
        total_time = 0.0
        
        for i in range(n_tests):
            start_time = time.perf_counter()
            _ = self.index.search(query, k=5)
            end_time = time.perf_counter()
            total_time += (end_time - start_time)
        
        avg_time_ms = (total_time / n_tests) * 1000
        
        print(f"平均搜索时间: {avg_time_ms:.4f} ms")
        
        # 验证性能要求
        self.assertLess(avg_time_ms, 5.0, 
                         f"平均搜索时间 {avg_time_ms:.2f}ms，超过 5ms 要求")
        
        print("TR-4.1 通过！")
    
    def test_tr41_batch_search_performance(self):
        """TR-4.1 批量搜索性能测试"""
        n_students = 500
        n_templates_per_student = 1
        total_templates = n_students * n_templates_per_student
        
        student_ids = []
        features = np.random.rand(total_templates, self.dim).astype('float32')
        
        for i in range(n_students):
            student_ids.append(f"student_{i:03d}")
        
        self.index.add_templates_batch(student_ids, features)
        
        # 批量查询
        n_queries = 10
        queries = features[:n_queries]
        
        # 预热
        for _ in range(10):
            _ = self.index.batch_search(queries, k=5)
        
        # 性能测试
        n_tests = 50
        total_time = 0.0
        
        for i in range(n_tests):
            start_time = time.perf_counter()
            _ = self.index.batch_search(queries, k=5)
            end_time = time.perf_counter()
            total_time += (end_time - start_time)
        
        avg_time_ms = (total_time / n_tests) * 1000
        avg_per_query_ms = avg_time_ms / n_queries
        
        print(f"批量搜索平均总时间: {avg_time_ms:.4f} ms ({n_queries} 个查询)")
        print(f"平均每个查询时间: {avg_per_query_ms:.4f} ms")
        
        # 验证性能要求
        self.assertLess(avg_per_query_ms, 5.0, 
                         f"平均每个查询 {avg_per_query_ms:.2f}ms，超过 5ms 要求")


def run_tests():
    """运行所有测试"""
    if not FAISS_AVAILABLE:
        print("警告: FAISS 未安装，无法运行测试")
        print("请运行: pip install faiss-cpu")
        return
    
    print("=" * 60)
    print("FAISS 索引模块测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestFaissIndex))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("所有测试通过！")
    else:
        print(f"测试失败: {len(result.failures) + len(result.errors)} 个")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
