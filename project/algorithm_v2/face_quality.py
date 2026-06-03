"""
明眸智签 v2.0 - 人脸质量评估模块
功能：清晰度、光照、姿态、遮挡综合打分
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional


class QualityScore:
    """质量分数容器"""
    def __init__(self):
        self.sharpness: float = 0.0
        self.brightness: float = 0.0
        self.pose: float = 0.0
        self.overall: float = 0.0


class FaceQualityAssessment:
    """人脸质量评估器"""
    
    def __init__(self):
        # 权重配置（可调） - 清晰度权重更高
        self.weights = {
            'sharpness': 0.60,
            'brightness': 0.20,
            'pose': 0.20
        }
    
    def assess_sharpness(self, face_img: np.ndarray) -> float:
        """
        评估清晰度（拉普拉斯方差）
        Returns: 0-1 分数，越高越清晰
        """
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # 使用更敏感的归一化，让模糊图像分数更低
        # 使用 sigmoid 函数来更平滑地过渡
        # 经验阈值：200以下模糊，800以上清晰
        if variance < 200:
            score = variance / 2000.0
        elif variance < 800:
            score = 0.1 + (variance - 200) / 750.0 * 0.7
        else:
            score = 0.8 + min((variance - 800) / 2000.0, 0.2)
        
        return float(np.clip(score, 0.0, 1.0))
    
    def assess_brightness(self, face_img: np.ndarray) -> float:
        """
        评估光照均匀性和亮度
        Returns: 0-1 分数，越高光照越好
        """
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        mean_bright = np.mean(gray)
        std_bright = np.std(gray)
        
        # 亮度适中且均匀得分高
        # 理想亮度：128 左右
        brightness_score = 1.0 - abs(mean_bright - 128) / 128.0
        # 均匀性：标准差越小越好
        uniformity_score = 1.0 - (std_bright / 128.0)
        
        score = 0.6 * brightness_score + 0.4 * uniformity_score
        return float(np.clip(score, 0.0, 1.0))
    
    def assess_pose(self, landmarks: Optional[np.ndarray] = None) -> float:
        """
        评估姿态（TODO: 需要完整 68 点或 3D 对齐）
        Returns: 0-1 分数，越正面越高
        """
        # 临时占位：假设都是正面（需后续实现 3D 姿态估计）
        return 0.8
    
    def assess(self, face_img: np.ndarray, landmarks: Optional[np.ndarray] = None) -> QualityScore:
        """
        综合质量评估
        Returns: QualityScore 对象
        """
        result = QualityScore()
        result.sharpness = self.assess_sharpness(face_img)
        result.brightness = self.assess_brightness(face_img)
        result.pose = self.assess_pose(landmarks)
        
        # 加权融合
        result.overall = (
            self.weights['sharpness'] * result.sharpness +
            self.weights['brightness'] * result.brightness +
            self.weights['pose'] * result.pose
        )
        
        return result
