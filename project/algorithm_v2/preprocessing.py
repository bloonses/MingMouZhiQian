"""
明眸智签 v2.0 - 预处理模块
功能：光照增强 + 姿态感知
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class LightEnhancer:
    """光照增强器"""
    
    @staticmethod
    def clahe_enhance(
        img: np.ndarray,
        clip_limit: float = 2.0,
        grid_size: int = 8,
        lab_only: bool = True
    ) -> np.ndarray:
        """
        CLAHE (限制对比度自适应直方图均衡化)
        
        Args:
            img: 输入图像 (BGR 格式)
            clip_limit: 对比度限制
            grid_size: 网格大小
            lab_only: 是否只在 LAB 亮度通道应用
        
        Returns:
            增强后的图像
        """
        if lab_only:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
            l = clahe.apply(l)
            
            lab = cv2.merge([l, a, b])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
            v = clahe.apply(v)
            
            hsv = cv2.merge([h, s, v])
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    @staticmethod
    def adaptive_gamma_correction(
        img: np.ndarray,
        gamma_min: float = 0.4,
        gamma_max: float = 2.0,
        target_brightness: float = 128.0
    ) -> np.ndarray:
        """
        自适应伽马校正
        
        Args:
            img: 输入图像 (BGR 格式)
            gamma_min: 最小 gamma 值
            gamma_max: 最大 gamma 值
            target_brightness: 目标亮度 (0-255)
        
        Returns:
            校正后的图像
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_bright = np.mean(gray)
        std_bright = np.std(gray)
        
        # 自适应计算 gamma 值
        brightness_ratio = target_brightness / (mean_bright + 1e-6)
        gamma = np.clip(1.0 / brightness_ratio, gamma_min, gamma_max)
        
        # 也考虑标准差：光照越不均匀，调整幅度越大
        if std_bright > 80:
            gamma = gamma * 0.9 if gamma < 1.0 else gamma * 1.1
            gamma = np.clip(gamma, gamma_min, gamma_max)
        
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                          for i in np.arange(0, 256)]).astype("uint8")
        
        return cv2.LUT(img, table)
    
    @staticmethod
    def histogram_stretching(img: np.ndarray, percentile: float = 2.0) -> np.ndarray:
        """
        直方图拉伸（百分比截断）
        
        Args:
            img: 输入图像 (BGR 格式)
            percentile: 截断百分比
        
        Returns:
            拉伸后的图像
        """
        p_low = np.percentile(img, percentile)
        p_high = np.percentile(img, 100 - percentile)
        
        img_stretched = np.clip((img - p_low) * 255.0 / (p_high - p_low), 0, 255).astype(np.uint8)
        return img_stretched
    
    @staticmethod
    def enhance_pipeline(
        img: np.ndarray,
        use_gamma: bool = True,
        use_clahe: bool = True,
        use_stretching: bool = False
    ) -> np.ndarray:
        """
        综合增强流水线
        
        Args:
            img: 输入图像
            use_gamma: 是否使用伽马校正
            use_clahe: 是否使用 CLAHE
            use_stretching: 是否使用直方图拉伸
        
        Returns:
            增强后的图像
        """
        result = img.copy()
        
        if use_gamma:
            result = LightEnhancer.adaptive_gamma_correction(result)
        
        if use_stretching:
            result = LightEnhancer.histogram_stretching(result)
        
        if use_clahe:
            result = LightEnhancer.clahe_enhance(result)
        
        return result
    
    @staticmethod
    def get_brightness_stats(img: np.ndarray) -> Tuple[float, float, float, float]:
        """
        获取亮度统计信息
        
        Args:
            img: 输入图像
        
        Returns:
            (mean, std, min, max) 亮度统计
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_bright = np.mean(gray)
        std_bright = np.std(gray)
        min_bright = np.min(gray)
        max_bright = np.max(gray)
        return mean_bright, std_bright, min_bright, max_bright


class PoseAwareMatcher:
    """姿态感知匹配器（模板选择 + 相似度衰减）"""
    
    @staticmethod
    def pose_similarity_weight(
        query_pose: Tuple[float, float, float],
        template_pose: Tuple[float, float, float],
        yaw_weight: float = 0.5,
        pitch_weight: float = 0.35,
        roll_weight: float = 0.15
    ) -> float:
        """
        计算姿态相似度权重
        
        Args:
            query_pose: (yaw, pitch, roll) 查询人脸姿态 (角度)
            template_pose: (yaw, pitch, roll) 模板姿态 (角度)
            yaw_weight: 偏航角权重
            pitch_weight: 俯仰角权重
            roll_weight: 翻滚角权重
        
        Returns:
            0-1 权重，姿态越接近越高
        """
        yaw_diff = abs(query_pose[0] - template_pose[0])
        pitch_diff = abs(query_pose[1] - template_pose[1])
        roll_diff = abs(query_pose[2] - template_pose[2])
        
        # 归一化差值（假设最大角度为 90 度）
        yaw_norm = min(yaw_diff / 90.0, 1.0)
        pitch_norm = min(pitch_diff / 90.0, 1.0)
        roll_norm = min(roll_diff / 90.0, 1.0)
        
        # 加权组合
        combined_diff = (
            yaw_weight * yaw_norm +
            pitch_weight * pitch_norm +
            roll_weight * roll_norm
        )
        
        # 使用高斯函数计算权重，差值越大权重越低
        sigma = 0.3
        weight = np.exp(-(combined_diff ** 2) / (2 * sigma ** 2))
        
        return float(np.clip(weight, 0.0, 1.0))
    
    @staticmethod
    def decay_similarity_by_pose(
        similarity: float,
        pose_diff: float,
        max_decay: float = 0.4,
        decay_type: str = "exponential"
    ) -> float:
        """
        根据姿态差衰减相似度
        
        Args:
            similarity: 原始相似度 (0-1)
            pose_diff: 姿态差 (0-1，越大差越多)
            max_decay: 最大衰减比例
            decay_type: 衰减类型 ("linear", "exponential", "quadratic")
        
        Returns:
            衰减后的相似度
        """
        if decay_type == "linear":
            decay_factor = 1.0 - max_decay * pose_diff
        elif decay_type == "quadratic":
            decay_factor = 1.0 - max_decay * (pose_diff ** 2)
        elif decay_type == "exponential":
            decay_factor = np.exp(-max_decay * pose_diff)
        else:
            decay_factor = 1.0 - max_decay * pose_diff
        
        return float(similarity * decay_factor)
    
    @staticmethod
    def calculate_pose_diff(
        pose1: Tuple[float, float, float],
        pose2: Tuple[float, float, float]
    ) -> float:
        """
        计算两个姿态之间的差异 (0-1)
        
        Args:
            pose1: (yaw, pitch, roll) 第一个姿态
            pose2: (yaw, pitch, roll) 第二个姿态
        
        Returns:
            姿态差异 (0-1)
        """
        yaw_diff = abs(pose1[0] - pose2[0])
        pitch_diff = abs(pose1[1] - pose2[1])
        roll_diff = abs(pose1[2] - pose2[2])
        
        yaw_norm = min(yaw_diff / 90.0, 1.0)
        pitch_norm = min(pitch_diff / 90.0, 1.0)
        roll_norm = min(roll_diff / 90.0, 1.0)
        
        combined_diff = (yaw_norm + pitch_norm + roll_norm) / 3.0
        return float(np.clip(combined_diff, 0.0, 1.0))
    
    @staticmethod
    def select_best_template(
        query_pose: Tuple[float, float, float],
        template_poses: list,
        top_k: int = 3
    ) -> list:
        """
        根据姿态选择最匹配的模板
        
        Args:
            query_pose: 查询人脸姿态
            template_poses: 模板姿态列表 [(pose, template_id), ...]
            top_k: 返回前 K 个最匹配的模板
        
        Returns:
            排序后的模板索引列表，最匹配的在前
        """
        scores = []
        for idx, (pose, template_id) in enumerate(template_poses):
            weight = PoseAwareMatcher.pose_similarity_weight(query_pose, pose)
            scores.append((weight, idx, template_id))
        
        # 按权重降序排序
        scores.sort(reverse=True, key=lambda x: x[0])
        
        # 返回前 K 个
        return [(idx, template_id, weight) for weight, idx, template_id in scores[:top_k]]


class FacePreprocessor:
    """综合预处理类 - 整合光照增强和姿态处理"""
    
    def __init__(self):
        self.light_enhancer = LightEnhancer()
        self.pose_matcher = PoseAwareMatcher()
    
    def preprocess(
        self,
        img: np.ndarray,
        enhance: bool = True,
        normalize_size: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        完整的人脸预处理流程
        
        Args:
            img: 输入人脸图像
            enhance: 是否进行光照增强
            normalize_size: 是否归一化到指定尺寸 (width, height)
        
        Returns:
            预处理后的图像
        """
        result = img.copy()
        
        if enhance:
            result = self.light_enhancer.enhance_pipeline(result)
        
        if normalize_size is not None:
            result = cv2.resize(result, normalize_size, interpolation=cv2.INTER_AREA)
        
        return result
