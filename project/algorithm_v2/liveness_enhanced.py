"""
明眸智签 v2.0 - 增强活体检测模块
功能：眨眼检测(EAR) + 鼻尖移动 + 活体分类器（三模态融合）
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import os
import sys

# 尝试导入 onnxruntime
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
    ort = None


class TextureLivenessClassifier:
    """
    基于图像纹理分析的轻量级活体检测分类器

    该分类器使用多种图像特征来判断是否为真实人脸:
    1. 拉普拉斯方差 - 清晰度/纹理丰富度
    2. HSV 色彩空间分析 - 色彩保真度
    3. 频域分析 - 屏幕摩尔纹检测
    4. 噪声估计 - 照片 vs 真实人脸

    无需下载外部模型，直接使用内置特征进行判断
    """

    def __init__(self):
        # 分类器参数
        self.blur_threshold = 100  # 拉普拉斯方差阈值
        self.texture_threshold = 0.1
        self.fft_threshold = 0.15

        # 历史分数用于平滑
        self.score_history = []
        self.max_history = 10

    def _compute_laplacian_variance(self, gray: np.ndarray) -> float:
        """计算拉普拉斯方差（清晰度/纹理）"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)

    def _compute_hsv_features(self, img: np.ndarray) -> Dict[str, float]:
        """
        计算 HSV 色彩空间特征
        翻拍照片通常会有色彩失真
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # H 通道分布（色相）
        h_channel = hsv[:, :, 0]
        h_std = np.std(h_channel)

        # S 通道饱和度
        s_channel = hsv[:, :, 1]
        s_mean = np.mean(s_channel)
        s_std = np.std(s_channel)

        # V 通道亮度
        v_channel = hsv[:, :, 2]
        v_mean = np.mean(v_channel)
        v_std = np.std(v_channel)

        return {
            'h_std': float(h_std),
            's_mean': float(s_mean),
            's_std': float(s_std),
            'v_mean': float(v_mean),
            'v_std': float(v_std)
        }

    def _compute_fft_features(self, gray: np.ndarray) -> float:
        """
        计算频域特征
        屏幕翻拍通常会产生摩尔纹，在频域有特定模式
        """
        # 缩放图像以加快 FFT 速度
        h, w = gray.shape
        scale = min(128 / h, 128 / w, 1.0)
        if scale < 1.0:
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)))

        # 计算 FFT
        f = np.fft.fft2(gray.astype(np.float32))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        # 计算高频能量比例
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        # 创建环形掩码
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - center_w) ** 2 + (y - center_h) ** 2)

        # 高频区域（外围）
        high_freq_mask = dist > min(h, w) * 0.3
        low_freq_mask = ~high_freq_mask

        high_energy = np.sum(magnitude[high_freq_mask])
        total_energy = np.sum(magnitude) + 1e-10

        high_freq_ratio = high_energy / total_energy

        return float(high_freq_ratio)

    def _compute_noise_features(self, gray: np.ndarray) -> float:
        """
        估计图像噪声水平
        真实人脸和翻拍照片的噪声模式不同
        """
        # 使用高通滤波估计噪声
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = gray.astype(np.float32) - blur.astype(np.float32)
        noise_std = np.std(noise)

        # 归一化
        noise_score = np.clip(noise_std / 15.0, 0, 1.0)

        return float(noise_score)

    def _analyze_texture_complexity(self, gray: np.ndarray) -> float:
        """
        分析纹理复杂度
        使用 Sobel 边缘检测
        """
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)

        # 计算边缘强度均值
        edge_mean = np.mean(magnitude)
        edge_score = np.clip(edge_mean / 50.0, 0, 1.0)

        return float(edge_score)

    def predict(self, face_img: np.ndarray) -> float:
        """
        预测活体分数

        Args:
            face_img: 人脸图像 (BGR 格式)

        Returns:
            活体分数 (0-1)，越高越可能是真实人脸
        """
        if face_img is None or face_img.size == 0 or face_img.shape[0] < 20:
            return 0.5

        # 转换为灰度图
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

        # 1. 拉普拉斯方差（清晰度/纹理）
        laplacian_var = self._compute_laplacian_variance(gray)

        # 2. HSV 特征
        hsv_features = self._compute_hsv_features(face_img)

        # 3. 频域特征
        fft_ratio = self._compute_fft_features(gray)

        # 4. 噪声特征
        noise_score = self._compute_noise_features(gray)

        # 5. 纹理复杂度
        texture_score = self._analyze_texture_complexity(gray)

        # 计算各维度分数
        # 清晰度分数（太低可能是模糊照片）
        if laplacian_var < 100:
            clarity_score = laplacian_var / 100.0 * 0.3
        elif laplacian_var < 500:
            clarity_score = 0.3 + (laplacian_var - 100) / 400.0 * 0.4
        else:
            clarity_score = 0.7 + min((laplacian_var - 500) / 1000.0, 0.3)
        clarity_score = np.clip(clarity_score, 0, 1)

        # 色彩保真度分数（翻拍照片色彩可能失真）
        # 正常照片的饱和度应该在合理范围
        s_score = 1.0 - abs(hsv_features['s_mean'] - 80) / 80.0
        s_score = np.clip(s_score, 0, 1)

        # 频域分数（摩尔纹检测）
        # 高频比例太低可能表示翻拍
        fft_score = 1.0 if fft_ratio > 0.1 else fft_ratio / 0.1
        fft_score = np.clip(fft_score, 0, 1)

        # 综合分数
        raw_score = (
            clarity_score * 0.30 +    # 清晰度权重
            s_score * 0.15 +           # 色彩保真度
            fft_score * 0.15 +        # 摩尔纹检测
            noise_score * 0.20 +      # 噪声模式
            texture_score * 0.20      # 纹理复杂度
        )

        # 加入历史平滑
        self.score_history.append(raw_score)
        if len(self.score_history) > self.max_history:
            self.score_history.pop(0)

        # 使用滑动平均平滑结果
        smoothed_score = np.mean(self.score_history)

        return float(np.clip(smoothed_score, 0.0, 1.0))

    def reset(self):
        """重置历史状态"""
        self.score_history = []


class ONNXLivenessClassifier:
    """
    ONNX 活体分类器包装器

    支持加载外部 ONNX 模型进行活体检测
    如果没有可用的 ONNX 模型，自动回退到纹理分析方案
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化 ONNX 分类器

        Args:
            model_path: ONNX 模型路径，如果为 None 则使用纹理分析方案
        """
        self.model_path = model_path
        self.session = None
        self.use_texture_fallback = True

        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
        else:
            print("未找到 ONNX 活体模型，使用内置纹理分析方案")
            self.texture_classifier = TextureLivenessClassifier()

    def _load_model(self, model_path: str):
        """加载 ONNX 模型"""
        if not ONNXRUNTIME_AVAILABLE:
            print("onnxruntime 未安装，使用纹理分析方案作为替代")
            self.texture_classifier = TextureLivenessClassifier()
            return

        try:
            print(f"正在加载 ONNX 活体模型: {model_path}")
            self.session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider', 'CUDAExecutionProvider']
            )
            self.use_texture_fallback = False
            print("ONNX 活体模型加载成功")
        except Exception as e:
            print(f"ONNX 模型加载失败: {e}，使用纹理分析方案作为替代")
            self.texture_classifier = TextureLivenessClassifier()
            self.use_texture_fallback = True

    def _preprocess_for_onnx(self, face_img: np.ndarray) -> np.ndarray:
        """
        预处理图像以适应 ONNX 模型

        Args:
            face_img: 人脸图像 (BGR)

        Returns:
            预处理后的图像 (NCHW 格式)
        """
        # 缩放到模型输入大小（假设 128x128）
        input_size = (128, 128)
        resized = cv2.resize(face_img, input_size)

        # BGR -> RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # 归一化
        normalized = rgb.astype(np.float32) / 255.0

        # 转换为 NCHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # 添加批次维度
        batched = np.expand_dims(transposed, axis=0)

        return batched

    def predict(self, face_img: np.ndarray) -> float:
        """
        预测活体分数

        Args:
            face_img: 人脸图像 (BGR)

        Returns:
            活体分数 (0-1)
        """
        if self.use_texture_fallback or self.session is None:
            return self.texture_classifier.predict(face_img)

        try:
            # 预处理
            input_data = self._preprocess_for_onnx(face_img)

            # 获取输入输出名称
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name

            # 推理
            result = self.session.run([output_name], {input_name: input_data})

            # 解析结果（假设输出是概率）
            score = float(result[0][0][1])  # 通常 [0] 是攻击，[1] 是活体

            return np.clip(score, 0.0, 1.0)

        except Exception as e:
            print(f"ONNX 推理失败: {e}，使用纹理分析方案")
            return self.texture_classifier.predict(face_img)

    def reset(self):
        """重置状态"""
        if hasattr(self, 'texture_classifier'):
            self.texture_classifier.reset()


class LivenessClassifier:
    """
    活体分类器统一接口

    自动选择最佳可用方案:
    1. ONNX 活体模型（如果可用）
    2. 纹理分析方案（内置，无需下载）
    """

    def __init__(self, model_dir: Optional[str] = None):
        """
        初始化活体分类器

        Args:
            model_dir: 模型目录，搜索该目录下的 ONNX 模型
        """
        self.model_dir = model_dir
        self.classifier = None

        # 查找可用的 ONNX 模型
        onnx_model = self._find_onnx_model()

        if onnx_model:
            self.classifier = ONNXLivenessClassifier(onnx_model)
        else:
            # 使用纹理分析方案
            print("初始化纹理分析活体分类器...")
            self.classifier = TextureLivenessClassifier()

    def _find_onnx_model(self) -> Optional[str]:
        """查找可用的 ONNX 活体模型"""
        if not self.model_dir or not os.path.exists(self.model_dir):
            # 尝试默认位置
            default_dirs = [
                os.path.join(os.path.dirname(__file__), '..', '.insightface', 'models', 'liveness'),
                os.path.join(os.path.dirname(__file__), '..', '.insightface', 'models'),
            ]
            for d in default_dirs:
                if os.path.exists(d):
                    self.model_dir = d
                    break

        if not self.model_dir or not os.path.exists(self.model_dir):
            return None

        # 搜索 ONNX 文件
        for filename in os.listdir(self.model_dir):
            if filename.endswith('.onnx'):
                # 排除明显不是活体模型的文件
                # 活体模型通常名称包含 liveness, anti_spoofing, fas 等
                lower_name = filename.lower()
                if any(keyword in lower_name for keyword in ['liveness', 'antispoof', 'anti_spoof', 'fas', 'spoof']):
                    return os.path.join(self.model_dir, filename)

        return None

    def predict(self, face_img: np.ndarray) -> float:
        """
        预测活体分数

        Args:
            face_img: 人脸图像 (BGR)

        Returns:
            活体分数 (0-1)
        """
        if self.classifier is None:
            return 0.5
        return self.classifier.predict(face_img)

    def reset(self):
        """重置状态"""
        if self.classifier:
            self.classifier.reset()


class BlinkDetector:
    """眨眼检测器 - 支持 InsightFace 5 点模型和传统 68 点模型"""
    
    def __init__(self):
        # EAR 阈值（经验值）
        self.ear_threshold = 0.25
        # 连续帧数判定眨眼
        self.consec_frames = 2
        # 最大历史帧数
        self.max_history = 30
        
        self.ear_history = []
        self.blink_counter = 0
        self.blink_detected = False
        self.was_blinking = False
    
    @staticmethod
    def eye_aspect_ratio_from_5pts(left_eye: np.ndarray, right_eye: np.ndarray, 
                                  face_bbox: Optional[np.ndarray] = None) -> float:
        """
        从 InsightFace 5 点模型计算简化版 EAR
        InsightFace 5 点: [左眼, 右眼, 鼻尖, 左嘴角, 右嘴角]
        
        Args:
            left_eye: 左眼坐标 (x, y)
            right_eye: 右眼坐标 (x, y)
            face_bbox: 人脸框 [x1, y1, x2, y2]，用于归一化
        Returns:
            简化版 EAR 值
        """
        # 两眼距离作为参考
        eye_distance = np.linalg.norm(left_eye - right_eye)
        
        if face_bbox is not None:
            # 用人脸高度做归一化
            face_height = face_bbox[3] - face_bbox[1]
            norm_factor = face_height if face_height > 0 else eye_distance
        else:
            norm_factor = eye_distance
        
        if norm_factor <= 0:
            return 0.3  # 默认值
        
        # 由于只有单眼点，我们使用基于历史帧的变化检测
        # 这里返回一个基于距离的比例作为参考
        ear_estimate = min(0.5, eye_distance / (norm_factor * 0.4))
        return ear_estimate
    
    @staticmethod
    def eye_aspect_ratio_68pts(eye_landmarks: np.ndarray) -> float:
        """
        从 68 点模型计算标准 EAR
        Args:
            eye_landmarks: 单眼 6 个关键点
        Returns:
            EAR 值
        """
        # 垂直距离
        A = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
        B = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
        # 水平距离
        C = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
        
        if C <= 0:
            return 0.3
        
        # EAR 公式
        ear = (A + B) / (2.0 * C)
        return ear
    
    def detect_from_5pts(self, landmarks: np.ndarray, 
                        face_bbox: Optional[np.ndarray] = None) -> Tuple[bool, float]:
        """
        从 InsightFace 5 点模型检测眨眼
        使用基于眼距变化的方法
        """
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        
        # 计算两眼距离
        eye_distance = np.linalg.norm(left_eye - right_eye)
        
        # 将距离加入历史
        self.ear_history.append(eye_distance)
        if len(self.ear_history) > self.max_history:
            self.ear_history.pop(0)
        
        blink_occurred = False
        
        if len(self.ear_history) >= 6:
            # 计算最近一段时间的平均值和标准差
            recent = np.array(self.ear_history[-6:])
            mean_dist = np.mean(recent)
            std_dist = np.std(recent)
            
            # 标准化当前距离
            current_dist = recent[-1]
            
            # 检测距离变化（眨眼时眼睛闭合会导致检测点位置变化）
            # 使用相对变化率
            if len(self.ear_history) > 10:
                prev_mean = np.mean(self.ear_history[-10:-5])
                change_ratio = abs(current_dist - prev_mean) / (prev_mean + 1e-6)
                
                # 变化超过一定阈值可能表示眨眼
                if change_ratio > 0.03:
                    self.blink_counter += 1
                else:
                    if self.blink_counter >= self.consec_frames:
                        blink_occurred = True
                    self.blink_counter = 0
            
            # 归一化的 EAR 替代值
            avg_ear = 0.3 + (std_dist / (mean_dist + 1e-6)) * 0.4
        else:
            avg_ear = 0.3
            self.blink_counter = 0
        
        # 限制范围
        avg_ear = np.clip(avg_ear, 0.1, 0.6)
        
        return blink_occurred, avg_ear
    
    def detect_from_68pts(self, landmarks: np.ndarray) -> Tuple[bool, float]:
        """从 68 点模型检测眨眼"""
        left_eye_idx = list(range(36, 42))
        right_eye_idx = list(range(42, 48))
        
        left_eye = landmarks[left_eye_idx]
        right_eye = landmarks[right_eye_idx]
        
        left_ear = self.eye_aspect_ratio_68pts(left_eye)
        right_ear = self.eye_aspect_ratio_68pts(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        
        self.ear_history.append(avg_ear)
        if len(self.ear_history) > self.max_history:
            self.ear_history.pop(0)
        
        # 检测眨眼（EAR 从高变低再变高）
        blink_occurred = False
        
        # 当前是否在眨眼状态（眼睛闭合）
        is_blinking = avg_ear < self.ear_threshold
        
        if is_blinking:
            self.blink_counter += 1
        else:
            # 眼睛重新睁开，检查之前是否有足够的闭合帧数
            if self.blink_counter >= self.consec_frames and self.was_blinking:
                blink_occurred = True
            self.blink_counter = 0
        
        self.was_blinking = is_blinking
        
        return blink_occurred, avg_ear
    
    def detect(self, landmarks: np.ndarray, 
              face_bbox: Optional[np.ndarray] = None) -> Tuple[bool, float]:
        """
        统一的眨眼检测接口
        Args:
            landmarks: 关键点数组 (5 点或 68 点)
            face_bbox: 人脸框，用于 5 点模型
        Returns:
            (是否检测到眨眼, 平均 EAR/替代值)
        """
        if len(landmarks) == 5:
            return self.detect_from_5pts(landmarks, face_bbox)
        elif len(landmarks) >= 68:
            return self.detect_from_68pts(landmarks)
        else:
            # 不支持的关键点数量
            return False, 0.3


class LivenessResult:
    """活体检测结果"""
    def __init__(self):
        self.is_live: bool = False
        self.nose_score: float = 0.0
        self.blink_score: float = 0.0
        self.classifier_score: float = 0.0
        self.overall_score: float = 0.0
        self.blink_count: int = 0


class EnhancedLivenessDetector:
    """增强活体检测器 - 多模态融合（鼻尖 40% + 眨眼 30% + 分类器 30%）"""

    # 活体分类器实例（类级别共享）
    _liveness_classifier = None

    def __init__(self):
        self.nose_tracker_history = []
        self.blink_detector = BlinkDetector()
        self.total_blinks = 0
        self.frame_count = 0

        # 权重配置：鼻尖 40% + 眨眼 30% + 分类器 30%
        self.weights = {
            'nose': 0.4,
            'blink': 0.3,
            'classifier': 0.3
        }

        # 最终判定阈值
        self.final_threshold = 0.55

        # 历史参数
        self.max_history = 30
        self.min_frames = 6

        # 初始化活体分类器
        self._init_liveness_classifier()

    def _init_liveness_classifier(self):
        """初始化活体分类器"""
        if EnhancedLivenessDetector._liveness_classifier is None:
            # 尝试从项目根目录的 .insightface/models 加载
            model_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                '.insightface', 'models', 'liveness'
            )
            EnhancedLivenessDetector._liveness_classifier = LivenessClassifier(model_dir)

    def _compute_nose_movement(self, nose_tip: np.ndarray) -> float:
        """计算鼻尖移动分数"""
        self.nose_tracker_history.append(nose_tip.copy())
        if len(self.nose_tracker_history) > self.max_history:
            self.nose_tracker_history.pop(0)

        if len(self.nose_tracker_history) < self.min_frames:
            return 0.0

        # 计算最近一段时间的移动范围
        recent = np.array(self.nose_tracker_history[-10:])
        x_range = np.max(recent[:, 0]) - np.min(recent[:, 0])
        y_range = np.max(recent[:, 1]) - np.min(recent[:, 1])
        movement = max(x_range, y_range)

        # 归一化到 0-1（10像素以上算有明显移动）
        # 使用 sigmoid 函数平滑过渡
        score = 1.0 / (1.0 + np.exp(-(movement - 8) / 3.0))
        return float(np.clip(score, 0.0, 1.0))

    def _compute_blink_score(self, blink_found: bool, avg_ear: float) -> float:
        """计算眨眼分数"""
        if blink_found:
            # 检测到眨眼，给高分
            return 1.0
        else:
            # 根据累计眨眼次数和 EAR 值给分
            if self.frame_count > 20 and self.total_blinks > 0:
                # 有过眨眼记录，给予基础分
                base_score = 0.6
            else:
                base_score = 0.3

            # 根据 EAR/替代值调整
            ear_factor = np.clip((0.5 - avg_ear) * 2.0, -0.2, 0.2)
            score = base_score + ear_factor

            return float(np.clip(score, 0.0, 1.0))

    def _compute_classifier_score(self, face_img: np.ndarray) -> float:
        """
        使用活体分类器计算分数

        Args:
            face_img: 人脸图像

        Returns:
            活体分数 (0-1)
        """
        if face_img is None or face_img.size == 0:
            return 0.5

        # 使用类级别共享的分类器
        if EnhancedLivenessDetector._liveness_classifier is not None:
            return EnhancedLivenessDetector._liveness_classifier.predict(face_img)

        return 0.5

    def get_score(self, face_img: np.ndarray, landmarks: np.ndarray,
                  nose_tip: Optional[np.ndarray] = None,
                  face_bbox: Optional[np.ndarray] = None) -> LivenessResult:
        """
        综合活体检测

        三模态融合:
        - 鼻尖移动: 40%
        - 眨眼检测: 30%
        - 活体分类器: 30%

        Args:
            face_img: 人脸图像
            landmarks: 关键点 (5 点或 68 点)
            nose_tip: 鼻尖坐标（可选）
            face_bbox: 人脸框（可选，用于 5 点模型）
        Returns:
            LivenessResult
        """
        result = LivenessResult()
        self.frame_count += 1

        # 获取鼻尖坐标
        if nose_tip is None:
            if len(landmarks) == 5:
                nose_tip = landmarks[2]
            elif len(landmarks) >= 68:
                nose_tip = landmarks[30]
            else:
                nose_tip = np.array([0, 0])

        # 1. 鼻尖移动分数 (40%)
        result.nose_score = self._compute_nose_movement(nose_tip)

        # 2. 眨眼检测分数 (30%)
        blink_found, avg_ear = self.blink_detector.detect(landmarks, face_bbox)
        if blink_found:
            self.total_blinks += 1

        result.blink_score = self._compute_blink_score(blink_found, avg_ear)
        result.blink_count = self.total_blinks

        # 3. 活体分类器 (30%) - 使用纹理分析或 ONNX 模型
        result.classifier_score = self._compute_classifier_score(face_img)

        # 4. 多模态加权融合
        result.overall_score = (
            self.weights['nose'] * result.nose_score +
            self.weights['blink'] * result.blink_score +
            self.weights['classifier'] * result.classifier_score
        )

        # 5. 最终判断
        result.is_live = result.overall_score > self.final_threshold

        return result

    def reset(self):
        """重置历史状态（切换班级时调用）"""
        self.nose_tracker_history = []
        self.blink_detector = BlinkDetector()
        self.total_blinks = 0
        self.frame_count = 0


class LivenessDetectorPool:
    """
    多人脸活体检测池
    为每个检测到的人脸维护独立的检测器
    """

    def __init__(self):
        self.detectors: Dict[int, EnhancedLivenessDetector] = {}

    def get_or_create(self, face_idx: int) -> EnhancedLivenessDetector:
        """获取或创建人脸对应的检测器"""
        if face_idx not in self.detectors:
            self.detectors[face_idx] = EnhancedLivenessDetector()
        return self.detectors[face_idx]

    def reset(self):
        """重置所有检测器"""
        self.detectors = {}
        # 重置类级别的活体分类器
        if EnhancedLivenessDetector._liveness_classifier is not None:
            EnhancedLivenessDetector._liveness_classifier.reset()


# 全局单例
_liveness_pool: Optional[LivenessDetectorPool] = None


def get_liveness_pool() -> LivenessDetectorPool:
    """获取活体检测池单例"""
    global _liveness_pool
    if _liveness_pool is None:
        _liveness_pool = LivenessDetectorPool()
    return _liveness_pool
