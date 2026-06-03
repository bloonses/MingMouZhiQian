"""
明眸智签 v2.0 - FAISS 向量索引模块
功能：加速大规模人脸库 k-NN 搜索
"""

import numpy as np
import json
import sys
from typing import List, Tuple, Optional, Dict

# FAISS 导入处理
FAISS_AVAILABLE = False
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    print("警告: FAISS 未安装。请运行: pip install faiss-cpu", file=sys.stderr)
    print("或者从 https://github.com/facebookresearch/faiss 安装", file=sys.stderr)


class SearchResult:
    """搜索结果"""
    def __init__(self, student_id: str, similarity: float, template_idx: int):
        self.student_id = student_id
        self.similarity = similarity
        self.template_idx = template_idx
    
    def __repr__(self):
        return f"SearchResult(student_id={self.student_id}, similarity={self.similarity:.4f}, template_idx={self.template_idx})"


class FaceVectorIndex:
    """人脸向量索引管理器"""
    
    def __init__(self, dim: int = 512):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS 不可用，无法创建 FaceVectorIndex")
        
        self.dim = dim
        # 内积搜索（余弦相似度，特征需要归一化）
        self.index = faiss.IndexFlatIP(dim)
        # 映射：向量索引 -> (student_id, template_idx)
        self.id_map: List[Tuple[str, int]] = []
        # 逆索引：student_id -> [向量索引列表]
        self.student_to_vecs: Dict[str, List[int]] = {}
    
    def add_template(self, student_id: str, feature: np.ndarray, template_idx: int = 0):
        """
        添加一个人脸模板
        Args:
            student_id: 学生 ID
            feature: 512 维特征（已归一化）
            template_idx: 模板序号（0,1,2...）
        """
        # 确保是行向量且归一化
        feature = feature.reshape(1, -1).astype('float32')
        feature = feature / np.linalg.norm(feature)
        
        # 添加到索引
        vec_idx = len(self.id_map)
        self.index.add(feature)
        self.id_map.append((student_id, template_idx))
        
        # 更新逆索引
        if student_id not in self.student_to_vecs:
            self.student_to_vecs[student_id] = []
        self.student_to_vecs[student_id].append(vec_idx)
    
    def add_templates_batch(self, student_ids: List[str], features: np.ndarray, template_indices: Optional[List[int]] = None):
        """
        批量添加人脸模板，提高性能
        Args:
            student_ids: 学生 ID 列表
            features: 特征矩阵 (n_samples, dim)
            template_indices: 模板序号列表，可选
        """
        n_samples = features.shape[0]
        if template_indices is None:
            template_indices = [0] * n_samples
        
        if len(student_ids) != n_samples or len(template_indices) != n_samples:
            raise ValueError("student_ids、features 和 template_indices 的长度必须一致")
        
        # 确保特征是 float32 并归一化
        features = features.astype('float32')
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        features = features / norms
        
        # 批量添加到索引
        start_idx = len(self.id_map)
        self.index.add(features)
        
        # 更新映射
        for i in range(n_samples):
            vec_idx = start_idx + i
            student_id = student_ids[i]
            template_idx = template_indices[i]
            self.id_map.append((student_id, template_idx))
            
            if student_id not in self.student_to_vecs:
                self.student_to_vecs[student_id] = []
            self.student_to_vecs[student_id].append(vec_idx)
    
    def remove_student(self, student_id: str):
        """
        移除学生的所有模板（通过重建索引实现）
        Args:
            student_id: 要移除的学生 ID
        """
        if student_id not in self.student_to_vecs:
            return
        
        # 收集需要保留的向量
        keep_indices = []
        for sid, vecs in self.student_to_vecs.items():
            if sid != student_id:
                keep_indices.extend(vecs)
        
        if not keep_indices and len(self.id_map) > 0:
            # 全部移除，重置索引
            self.index = faiss.IndexFlatIP(self.dim)
            self.id_map = []
            self.student_to_vecs = {}
            return
        
        # 重建索引
        if len(keep_indices) < len(self.id_map):
            # 获取所有向量
            if hasattr(self.index, 'reconstruct_n'):
                all_vectors = self.index.reconstruct_n(0, len(self.id_map))
            else:
                # 对于 IndexFlatIP，我们需要逐个重建
                all_vectors = []
                for i in range(len(self.id_map)):
                    all_vectors.append(self.index.reconstruct(i))
                all_vectors = np.array(all_vectors)
            
            # 筛选需要保留的向量
            keep_vectors = all_vectors[keep_indices]
            
            # 重建映射
            new_id_map = [self.id_map[i] for i in keep_indices]
            new_student_to_vecs: Dict[str, List[int]] = {}
            for new_idx, (sid, tid) in enumerate(new_id_map):
                if sid not in new_student_to_vecs:
                    new_student_to_vecs[sid] = []
                new_student_to_vecs[sid].append(new_idx)
            
            # 创建新索引
            new_index = faiss.IndexFlatIP(self.dim)
            if len(keep_vectors) > 0:
                new_index.add(keep_vectors)
            
            # 更新
            self.index = new_index
            self.id_map = new_id_map
            self.student_to_vecs = new_student_to_vecs
    
    def search(self, query: np.ndarray, k: int = 5) -> List[SearchResult]:
        """
        k-NN 搜索
        Args:
            query: 查询特征（已归一化）
            k: 返回 top-k
        Returns:
            SearchResult 列表，按相似度降序
        """
        query = query.reshape(1, -1).astype('float32')
        query = query / np.linalg.norm(query)
        
        distances, indices = self.index.search(query, k)
        
        results = []
        for i in range(min(k, len(indices[0]))):
            idx = indices[0][i]
            if idx < 0 or idx >= len(self.id_map):
                continue
            student_id, template_idx = self.id_map[idx]
            similarity = float(distances[0][i])
            results.append(SearchResult(student_id, similarity, template_idx))
        
        return results
    
    def batch_search(self, queries: np.ndarray, k: int = 5) -> List[List[SearchResult]]:
        """
        批量搜索（优化版本）
        Args:
            queries: 查询特征矩阵 (n_queries, dim)
            k: 返回 top-k
        Returns:
            每个查询的 SearchResult 列表
        """
        n_queries = queries.shape[0]
        queries = queries.astype('float32')
        
        # 批量归一化
        norms = np.linalg.norm(queries, axis=1, keepdims=True)
        # 避免除零
        norms[norms == 0] = 1.0
        queries = queries / norms
        
        # 批量搜索
        distances, indices = self.index.search(queries, k)
        
        # 构建结果
        all_results = []
        for q_idx in range(n_queries):
            results = []
            for i in range(min(k, indices.shape[1])):
                idx = indices[q_idx][i]
                if idx < 0 or idx >= len(self.id_map):
                    continue
                student_id, template_idx = self.id_map[idx]
                similarity = float(distances[q_idx][i])
                results.append(SearchResult(student_id, similarity, template_idx))
            all_results.append(results)
        
        return all_results
    
    def save(self, path: str):
        """
        保存索引和映射到文件
        Args:
            path: 保存路径（不包含扩展名）
        """
        faiss.write_index(self.index, path + '.index')
        with open(path + '.meta', 'w', encoding='utf-8') as f:
            json.dump({
                'id_map': self.id_map,
                'student_to_vecs': self.student_to_vecs,
                'dim': self.dim
            }, f, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str) -> 'FaceVectorIndex':
        """
        从文件加载索引
        Args:
            path: 加载路径（不包含扩展名）
        Returns:
            FaceVectorIndex 实例
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS 不可用，无法加载 FaceVectorIndex")
        
        index = faiss.read_index(path + '.index')
        with open(path + '.meta', 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        obj = cls(meta['dim'])
        obj.index = index
        obj.id_map = meta['id_map']
        obj.student_to_vecs = meta['student_to_vecs']
        return obj
    
    def __len__(self):
        return len(self.id_map)
    
    def get_student_count(self) -> int:
        """获取学生数量"""
        return len(self.student_to_vecs)
