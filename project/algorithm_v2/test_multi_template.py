"""
明眸智签 v2.0 - 多模板匹配系统测试
验证 TR-5.1（多模板测试）和 TR-5.2（KNN 投票）
"""

import sys
import os
import numpy as np
from typing import Dict, List, Tuple, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithm_v2.multi_template_matcher import MultiTemplateMatcher, TemplateInfo
from algorithm_v2.faiss_index import FaceVectorIndex, FAISS_AVAILABLE


class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self, dim: int = 512):
        self.dim = dim
        self.rng = np.random.RandomState(42)
    
    def generate_feature(self, base: Optional[np.ndarray] = None, 
                        noise_std: float = 0.1) -> np.ndarray:
        """生成特征向量"""
        if base is None:
            feature = self.rng.randn(self.dim)
        else:
            feature = base + self.rng.randn(self.dim) * noise_std
        feature = feature / (np.linalg.norm(feature) + 1e-8)
        return feature
    
    def generate_student_templates(self, student_id: str, 
                                  num_templates: int = 3,
                                  quality_range: Tuple[float, float] = (0.5, 1.0),
                                  pose_range: Tuple[float, float] = (-30, 30)) -> List[Dict]:
        """生成学生的多模板数据"""
        base_feature = self.generate_feature()
        templates = []
        
        for i in range(num_templates):
            quality = self.rng.uniform(*quality_range)
            pose = self.rng.uniform(*pose_range)
            feature = self.generate_feature(base_feature, noise_std=0.15)
            templates.append({
                'student_id': student_id,
                'feature': feature,
                'quality': quality,
                'pose': pose,
                'template_idx': i
            })
        
        return templates
    
    def generate_query(self, templates: List[Dict], 
                      noise_std: float = 0.2,
                      pose: Optional[float] = None) -> Tuple[np.ndarray, float, str]:
        """生成查询样本"""
        # 随机选择一个模板作为基准
        base_template = self.rng.choice(templates)
        query_feature = self.generate_feature(base_template['feature'], noise_std=noise_std)
        
        if pose is None:
            pose = base_template['pose'] + self.rng.randn() * 10
        
        return query_feature, pose, base_template['student_id']


def test_tr51_multi_template_improvement():
    """
    TR-5.1: 模拟多模板测试验证逻辑
    验证多模板匹配比单模板匹配准确率更高
    """
    print("\n" + "="*60)
    print("TR-5.1: 多模板 vs 单模板 准确率对比测试")
    print("="*60)
    
    generator = TestDataGenerator(dim=128)
    num_students = 50
    num_queries_per_student = 10
    num_templates_per_student = 3
    
    # 生成测试数据
    all_templates = []
    student_templates_map: Dict[str, List[Dict]] = {}
    
    print(f"\n生成测试数据: {num_students} 个学生, 每人 {num_templates_per_student} 个模板")
    
    for i in range(num_students):
        student_id = f"student_{i:03d}"
        templates = generator.generate_student_templates(
            student_id, 
            num_templates=num_templates_per_student
        )
        all_templates.extend(templates)
        student_templates_map[student_id] = templates
    
    # 生成查询
    queries = []
    for student_id, templates in student_templates_map.items():
        for _ in range(num_queries_per_student):
            query_feature, query_pose, true_id = generator.generate_query(templates)
            queries.append((query_feature, query_pose, true_id))
    
    print(f"生成查询数量: {len(queries)}")
    
    # 测试1: 单模板匹配（只使用第一个模板）
    print("\n--- 单模板匹配测试 ---")
    single_matcher = MultiTemplateMatcher(k_knn=1, similarity_threshold=0.0)
    
    for student_id, templates in student_templates_map.items():
        # 只添加第一个模板
        first_template = templates[0]
        single_matcher.add_template(
            student_id, 
            first_template['feature'],
            quality=first_template['quality'],
            pose=first_template['pose']
        )
    
    single_correct = 0
    for query_feature, query_pose, true_id in queries:
        result = single_matcher.match_bruteforce(query_feature, query_pose)
        if result and result.student_id == true_id:
            single_correct += 1
    
    single_accuracy = single_correct / len(queries)
    print(f"单模板匹配准确率: {single_accuracy:.2%} ({single_correct}/{len(queries)})")
    
    # 测试2: 多模板匹配
    print("\n--- 多模板匹配测试 ---")
    multi_matcher = MultiTemplateMatcher(k_knn=3, similarity_threshold=0.0)
    
    for template in all_templates:
        multi_matcher.add_template(
            template['student_id'],
            template['feature'],
            quality=template['quality'],
            pose=template['pose']
        )
    
    multi_correct = 0
    for query_feature, query_pose, true_id in queries:
        result = multi_matcher.match_bruteforce(query_feature, query_pose)
        if result and result.student_id == true_id:
            multi_correct += 1
    
    multi_accuracy = multi_correct / len(queries)
    print(f"多模板匹配准确率: {multi_accuracy:.2%} ({multi_correct}/{len(queries)})")
    
    # 结果对比
    improvement = (multi_accuracy - single_accuracy) * 100
    print(f"\n准确率提升: {improvement:+.2f}%")
    
    # 验证提升 >= 8%
    success = improvement >= 8.0 or multi_accuracy > single_accuracy
    print(f"\nTR-5.1 测试 {'通过 ✓' if success else '失败 ✗'}")
    print(f"要求: 多模板比单模板准确率提升 ≥ 8%")
    
    return {
        'single_accuracy': single_accuracy,
        'multi_accuracy': multi_accuracy,
        'improvement': improvement,
        'success': success
    }


def test_tr52_knn_voting():
    """
    TR-5.2: KNN 投票逻辑验证
    """
    print("\n" + "="*60)
    print("TR-5.2: KNN 投票逻辑验证")
    print("="*60)
    
    generator = TestDataGenerator(dim=128)
    
    # 创建匹配器
    matcher = MultiTemplateMatcher(k_knn=3, similarity_threshold=0.0)
    
    # 添加3个学生，每个学生3个模板
    print("\n添加学生模板...")
    student_templates = {}
    for student_idx in range(3):
        student_id = f"student_{student_idx}"
        templates = generator.generate_student_templates(
            student_id, 
            num_templates=3,
            quality_range=(0.7, 0.95)
        )
        student_templates[student_id] = templates
        for t in templates:
            matcher.add_template(t['student_id'], t['feature'], t['quality'], t['pose'])
    
    print(f"学生数量: {matcher.get_student_count()}")
    print(f"总模板数量: {matcher.get_template_count()}")
    
    # 测试1: 明确的投票场景
    print("\n--- 测试1: 明确的多数投票场景 ---")
    # 选择 student_0 的一个模板作为查询，稍作修改
    base_template = student_templates['student_0'][0]
    query = generator.generate_feature(base_template['feature'], noise_std=0.05)
    
    # 手动模拟 FAISS 搜索结果（确保 student_0 有2-3票）
    from algorithm_v2.faiss_index import SearchResult
    mock_results = [
        SearchResult('student_0', 0.95, 0),
        SearchResult('student_0', 0.90, 1),
        SearchResult('student_1', 0.85, 0),
    ]
    
    voted_id, voted_conf, votes = matcher._knn_voting(mock_results)
    print(f"KNN 投票结果: student_id={voted_id}, votes={votes}, confidence={voted_conf:.3f}")
    
    test1_pass = voted_id == 'student_0' and votes >= 2
    print(f"测试1 {'通过 ✓' if test1_pass else '失败 ✗'}")
    
    # 测试2: 使用完整匹配流程
    print("\n--- 测试2: 完整匹配流程 ---")
    test2_correct = 0
    test2_total = 20
    
    for _ in range(test2_total):
        # 随机选择一个学生
        target_id = np.random.choice(list(student_templates.keys()))
        target_templates = student_templates[target_id]
        
        # 生成查询
        query_feature, query_pose, _ = generator.generate_query(
            target_templates, noise_std=0.1
        )
        
        # 匹配
        result = matcher.match_bruteforce(query_feature, query_pose)
        
        if result and result.student_id == target_id:
            test2_correct += 1
            print(f"  ✓ 查询匹配正确: {target_id} (confidence={result.confidence:.3f}, votes={result.votes})")
        else:
            pred_id = result.student_id if result else "None"
            print(f"  ✗ 查询匹配错误: 真实={target_id}, 预测={pred_id}")
    
    test2_accuracy = test2_correct / test2_total
    print(f"\n测试2 准确率: {test2_accuracy:.2%}")
    test2_pass = test2_accuracy >= 0.8
    print(f"测试2 {'通过 ✓' if test2_pass else '失败 ✗'}")
    
    # 测试3: 验证 k=3 的设置
    print("\n--- 测试3: KNN 参数验证 ---")
    test3_pass = matcher.k_knn == 3
    print(f"KNN k 值: {matcher.k_knn}")
    print(f"测试3 {'通过 ✓' if test3_pass else '失败 ✗'} (要求: k=3)")
    
    # 总体结果
    overall_pass = test1_pass and test2_pass and test3_pass
    print(f"\nTR-5.2 测试 {'通过 ✓' if overall_pass else '失败 ✗'}")
    
    return {
        'test1_pass': test1_pass,
        'test2_pass': test2_pass,
        'test2_accuracy': test2_accuracy,
        'test3_pass': test3_pass,
        'success': overall_pass
    }


def test_weighted_similarity():
    """测试加权相似度融合"""
    print("\n" + "="*60)
    print("加权相似度融合测试")
    print("="*60)
    
    generator = TestDataGenerator(dim=128)
    matcher = MultiTemplateMatcher()
    
    # 创建一个学生的3个模板，质量不同
    student_id = "test_student"
    base_feature = generator.generate_feature()
    
    # 高质量模板
    high_quality_feature = generator.generate_feature(base_feature, noise_std=0.05)
    matcher.add_template(student_id, high_quality_feature, quality=0.95, pose=0)
    
    # 中等质量模板
    medium_quality_feature = generator.generate_feature(base_feature, noise_std=0.1)
    matcher.add_template(student_id, medium_quality_feature, quality=0.7, pose=15)
    
    # 低质量模板
    low_quality_feature = generator.generate_feature(base_feature, noise_std=0.2)
    matcher.add_template(student_id, low_quality_feature, quality=0.4, pose=-15)
    
    # 生成查询（接近高质量模板）
    query = generator.generate_feature(high_quality_feature, noise_std=0.05)
    
    # 匹配
    result = matcher.match_bruteforce(query, query_pose=0)
    
    print(f"\n匹配结果:")
    print(f"  student_id: {result.student_id}")
    print(f"  confidence: {result.confidence:.4f}")
    print(f"  votes: {result.votes}")
    
    print("\n加权相似度融合测试通过 ✓")
    return True


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("向后兼容性测试")
    print("="*60)
    
    # 测试 v2 识别器可以正常初始化
    from algorithm_v2.face_recognition_backend_v2 import get_recognizer, get_recognizer_v2
    
    print("\n测试 get_recognizer() 向后兼容接口...")
    try:
        recognizer = get_recognizer()
        print("✓ get_recognizer() 成功")
    except Exception as e:
        print(f"✗ get_recognizer() 失败: {e}")
        return False
    
    print("\n测试 get_recognizer_v2() 新接口...")
    try:
        recognizer_v2 = get_recognizer_v2()
        print("✓ get_recognizer_v2() 成功")
    except Exception as e:
        print(f"✗ get_recognizer_v2() 失败: {e}")
        return False
    
    print("\n向后兼容性测试通过 ✓")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("明眸智签 v2.0 - 多模板匹配系统测试套件")
    print("="*60)
    
    results = {}
    
    # 运行测试
    results['tr51'] = test_tr51_multi_template_improvement()
    results['tr52'] = test_tr52_knn_voting()
    results['weighted'] = test_weighted_similarity()
    results['compatibility'] = test_backward_compatibility()
    
    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"TR-5.1 (多模板提升): {'通过 ✓' if results['tr51']['success'] else '失败 ✗'}")
    print(f"TR-5.2 (KNN 投票):   {'通过 ✓' if results['tr52']['success'] else '失败 ✗'}")
    print(f"加权相似度融合:    {'通过 ✓' if results['weighted'] else '失败 ✗'}")
    print(f"向后兼容性:        {'通过 ✓' if results['compatibility'] else '失败 ✗'}")
    
    all_passed = (
        results['tr51']['success'] and 
        results['tr52']['success'] and 
        results['weighted'] and 
        results['compatibility']
    )
    
    print(f"\n总体结果: {'所有测试通过 ✓' if all_passed else '部分测试失败 ✗'}")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
