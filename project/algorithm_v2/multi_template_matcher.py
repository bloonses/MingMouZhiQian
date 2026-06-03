"""
明眸智签 v2.0 - 多模板匹配系统
功能：多模板加权相似度融合、KNN 投票、姿态自适应匹配
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter

from .faiss_index import FaceVectorIndex, SearchResult


class TemplateInfo:
    """模板信息"""
    def __init__(self, student_id: str, feature: np.ndarray, 
                 quality: float = 0.8, pose: float = 0.0, 
                 template_idx: int = 0):
        self.student_id = student_id
        self.feature = feature
        self.quality = quality
        self.pose = pose
        self.template_idx = template_idx


class MatchResult:
    """匹配结果"""
    def __init__(self, student_id: str, confidence: float, 
                 votes: int = 0, details: Optional[Dict] = None):
        self.student_id = student_id
        self.confidence = confidence
        self.votes = votes
        self.details = details or {}


class MultiTemplateMatcher:
    """多模板匹配器"""
    
    def __init__(self, k_knn: int = 3, similarity_threshold: float = 0.45):
        """
        Args:
            k_knn: KNN 投票的 k 值
            similarity_threshold: 相似度阈值
        """
        self.k_knn = k_knn
        self.similarity_threshold = similarity_threshold
        self.faiss_index: Optional[FaceVectorIndex] = None
        self.templates: Dict[str, List[TemplateInfo]] = {}
    
    def set_faiss_index(self, faiss_index: FaceVectorIndex):
        """设置 FAISS 索引"""
        self.faiss_index = faiss_index
    
    def add_template(self, student_id: str, feature: np.ndarray, 
                     quality: float = 0.8, pose: float = 0.0):
        """
        添加模板
        Args:
            student_id: 学生 ID
            feature: 特征向量
            quality: 质量分数 (0-1)
            pose: 姿态角度
        """
        if student_id not in self.templates:
            self.templates[student_id] = []
        
        template_idx = len(self.templates[student_id])
        template = TemplateInfo(student_id, feature, quality, pose, template_idx)
        self.templates[student_id].append(template)
        
        # 同步到 FAISS 索引
        if self.faiss_index is not None:
            self.faiss_index.add_template(student_id, feature, template_idx)
    
    def _weighted_similarity_fusion(self, query_feature: np.ndarray, 
                                   templates: List[TemplateInfo],
                                   query_pose: Optional[float] = None) -> Tuple[str, float]:
        """
        加权相似度融合
        Args:
            query_feature: 查询特征
            templates: 同一学生的模板列表
            query_pose: 查询的姿态（可选）
        Returns:
            (student_id, fused_similarity)
        """
        if not templates:
            return "", 0.0
        
        student_id = templates[0].student_id
        similarities = []
        weights = []
        
        for template in templates:
            # 计算余弦相似度
            sim = float(np.dot(query_feature, template.feature))
            
            # 质量权重：质量越高，权重越大
            quality_weight = template.quality
            
            # 姿态权重：姿态越接近，权重越大
            pose_weight = 1.0
            if query_pose is not None:
                # 姿态差异（假设 pose 是角度）
                pose_diff = abs(query_pose - template.pose)
                # 使用高斯函数衰减
                pose_weight = np.exp(-0.5 * (pose_diff / 30.0) ** 2)
            
            # 总权重
            total_weight = quality_weight * pose_weight
            
            similarities.append(sim)
            weights.append(total_weight)
        
        # 归一化权重
        weight_sum = sum(weights)
        if weight_sum > 0:
            normalized_weights = [w / weight_sum for w in weights]
        else:
            normalized_weights = [1.0 / len(weights)] * len(weights)
        
        # 加权融合
        fused_sim = float(np.sum(np.array(similarities) * np.array(normalized_weights)))
        
        return student_id, fused_sim
    
    def _knn_voting(self, search_results: List[SearchResult]) -> Tuple[Optional[str], float, int]:
        """
        KNN 投票
        Args:
            search_results: FAISS 搜索结果
        Returns:
            (best_student_id, best_confidence, votes)
        """
        if not search_results:
            return None, 0.0, 0
        
        # 取 top-k 结果
        k_results = search_results[:self.k_knn]
        
        # 收集所有学生 ID 及其最高相似度
        student_sims: Dict[str, List[float]] = {}
        for res in k_results:
            if res.student_id not in student_sims:
                student_sims[res.student_id] = []
            student_sims[res.student_id].append(res.similarity)
        
        # 统计投票
        votes = Counter()
        best_sim_per_student = {}
        
        for student_id, sims in student_sims.items():
            votes[student_id] = len(sims)
            best_sim_per_student[student_id] = max(sims)
        
        # 找出得票最多的学生
        if votes:
            # 先按票数，再按相似度
            sorted_students = sorted(
                votes.items(),
                key=lambda x: (x[1], best_sim_per_student[x[0]]),
                reverse=True
            )
            best_student_id = sorted_students[0][0]
            best_votes = sorted_students[0][1]
            best_confidence = best_sim_per_student[best_student_id]
            return best_student_id, best_confidence, best_votes
        
        return None, 0.0, 0
    
    def match_with_faiss(self, query_feature: np.ndarray, 
                        query_pose: Optional[float] = None) -> Optional[MatchResult]:
        """
        使用 FAISS 进行匹配（推荐，速度快）
        Args:
            query_feature: 查询特征
            query_pose: 查询的姿态（可选）
        Returns:
            MatchResult 或 None
        """
        if self.faiss_index is None:
            return None
        
        # FAISS 搜索（返回 top-2k 结果以确保有足够的候选项）
        search_results = self.faiss_index.search(query_feature, k=2 * self.k_knn)
        
        if not search_results:
            return None
        
        # KNN 投票
        voted_student, voted_confidence, votes = self._knn_voting(search_results)
        
        if voted_student is None:
            return None
        
        # 对该学生的所有模板进行加权融合，得到最终相似度
        if voted_student in self.templates:
            _, fused_sim = self._weighted_similarity_fusion(
                query_feature, self.templates[voted_student], query_pose
            )
            final_confidence = fused_sim
        else:
            final_confidence = voted_confidence
        
        # 检查阈值
        if final_confidence < self.similarity_threshold:
            return None
        
        return MatchResult(
            student_id=voted_student,
            confidence=final_confidence,
            votes=votes,
            details={
                "voted_confidence": voted_confidence,
                "fused_confidence": final_confidence
            }
        )
    
    def match_bruteforce(self, query_feature: np.ndarray,
                        query_pose: Optional[float] = None) -> Optional[MatchResult]:
        """
        暴力匹配（用于小数据集或 FAISS 不可用）
        Args:
            query_feature: 查询特征
            query_pose: 查询的姿态（可选）
        Returns:
            MatchResult 或 None
        """
        best_student = None
        best_sim = 0.0
        
        for student_id, templates in self.templates.items():
            _, fused_sim = self._weighted_similarity_fusion(
                query_feature, templates, query_pose
            )
            if fused_sim > best_sim:
                best_sim = fused_sim
                best_student = student_id
        
        if best_student is None or best_sim < self.similarity_threshold:
            return None
        
        return MatchResult(
            student_id=best_student,
            confidence=best_sim,
            votes=1,
            details={"method": "bruteforce"}
        )
    
    def match(self, query_feature: np.ndarray,
             query_pose: Optional[float] = None,
             use_faiss: bool = True) -> Optional[MatchResult]:
        """
        统一匹配接口
        """
        if use_faiss and self.faiss_index is not None:
            return self.match_with_faiss(query_feature, query_pose)
        else:
            return self.match_bruteforce(query_feature, query_pose)
    
    def clear(self):
        """清空所有模板"""
        self.templates = {}
        if self.faiss_index is not None:
            # 如果需要清空 FAISS 索引，需要重建
            dim = self.faiss_index.dim
            self.faiss_index = FaceVectorIndex(dim)
    
    def get_student_count(self) -> int:
        """获取学生数量"""
        return len(self.templates)
    
    def get_template_count(self, student_id: Optional[str] = None) -> int:
        """获取模板数量"""
        if student_id is None:
            return sum(len(templates) for templates in self.templates.values())
        elif student_id in self.templates:
            return len(self.templates[student_id])
        else:
            return 0
