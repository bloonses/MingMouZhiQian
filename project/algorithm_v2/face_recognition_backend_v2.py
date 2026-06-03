"""
明眸智签 v2.0 - 人脸检测识别后端（增强版）
功能：集成 InsightFace、FAISS 索引、质量评估、多模板匹配、增强活体检测
"""

import os
import base64
import time
import cv2
import numpy as np
import ssl
import json
from typing import Dict, List, Optional, Tuple, Any

from .faiss_index import FaceVectorIndex, FAISS_AVAILABLE
from .face_quality import FaceQualityAssessment
from .multi_template_matcher import MultiTemplateMatcher
from .liveness_enhanced import EnhancedLivenessDetector, LivenessDetectorPool
from .face_tracker import FaceTracker, BatchFaceRecognizer


MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


# 使用增强版活体检测池
_liveness_pool = LivenessDetectorPool()


def get_liveness_pool():
    return _liveness_pool


class FaceRecognizerV2:
    """增强版人脸识别器 - 集成多模板、FAISS、质量评估、人脸追踪"""
    
    def __init__(self, use_gpu: bool = False, use_v2_features: bool = True, 
                 use_tracking: bool = True):
        """
        Args:
            use_gpu: 是否使用 GPU
            use_v2_features: 是否启用 v2 增强特性（FAISS、多模板等）
            use_tracking: 是否启用人脸追踪
        """
        self.use_gpu = use_gpu
        self.use_v2_features = use_v2_features
        self.use_tracking = use_tracking
        self.use_real_models = False
        self.detector = None
        self.recognizer = None
        self.embedding_dim = 512
        
        # v2 增强特性
        self.faiss_index: Optional[FaceVectorIndex] = None
        self.multi_matcher: Optional[MultiTemplateMatcher] = None
        self.quality_assessor = FaceQualityAssessment()
        
        # 人脸追踪器
        self.tracker: Optional[FaceTracker] = None
        if self.use_tracking:
            self.tracker = FaceTracker()
        
        # 模板存储（向后兼容支持）
        self.templates: Dict[str, Any] = {}
        
        self._init_insightface()
        self._init_v2_features()
    
    def _init_insightface(self):
        """初始化 InsightFace 模型"""
        try:
            import insightface
            print('[FaceRecognizerV2] 正在初始化 InsightFace...')

            project_insightface = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.insightface')

            candidate_roots = [
                project_insightface,
                os.path.expanduser('~/.insightface'),
            ]

            self.analysis = None
            last_error = None

            for root in candidate_roots:
                try:
                    print(f'[FaceRecognizerV2] 尝试加载模型 from: {root}')

                    buffalo_path = os.path.join(root, 'models', 'buffalo_l')
                    if os.path.exists(buffalo_path) and len(os.listdir(buffalo_path)) > 0:
                        print(f'[FaceRecognizerV2] 找到本地模型文件，直接加载...')

                    self.analysis = insightface.app.FaceAnalysis(
                        name='buffalo_l',
                        root=root,
                        providers=['CPUExecutionProvider'] if not self.use_gpu else ['CUDAExecutionProvider', 'CPUExecutionProvider']
                    )
                    self.analysis.prepare(ctx_id=0 if self.use_gpu else -1, det_size=(640, 640))
                    print(f'[FaceRecognizerV2] 成功从 {root} 加载模型')
                    break
                except Exception as e:
                    last_error = e
                    print(f'[FaceRecognizerV2] 加载失败 from {root}: {e}')
                    continue

            if self.analysis is None:
                raise last_error or Exception('所有路径都加载失败')

            self.embedding_dim = 512
            self.use_real_models = True
            print('[FaceRecognizerV2] InsightFace 模型初始化成功')
        except Exception as e:
            print('[FaceRecognizerV2] InsightFace 加载失败，降级到模拟模式:', str(e))
            self.embedding_dim = 128
            self._init_mock()
    
    def _init_mock(self):
        """初始化模拟模式"""
        self.use_real_models = False
    
    def _init_v2_features(self):
        """初始化 v2 增强特性"""
        if not self.use_v2_features:
            return
        
        try:
            if FAISS_AVAILABLE:
                self.faiss_index = FaceVectorIndex(dim=self.embedding_dim)
                self.multi_matcher = MultiTemplateMatcher(k_knn=3, similarity_threshold=0.45)
                self.multi_matcher.set_faiss_index(self.faiss_index)
                print('[FaceRecognizerV2] FAISS 索引和多模板匹配器初始化成功')
            else:
                print('[FaceRecognizerV2] FAISS 不可用，使用暴力匹配')
                self.multi_matcher = MultiTemplateMatcher(k_knn=3, similarity_threshold=0.45)
        except Exception as e:
            print(f'[FaceRecognizerV2] v2 特性初始化失败: {e}')
            self.use_v2_features = False
    
    @staticmethod
    def base64_to_numpy(image_b64: str) -> np.ndarray:
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        image_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    
    @staticmethod
    def numpy_to_base64(img: np.ndarray) -> str:
        _, buffer = cv2.imencode('.jpg', img)
        return base64.b64encode(buffer).decode('utf-8')
    
    def detect_faces(self, img: np.ndarray) -> List[Dict]:
        if self.use_real_models:
            return self._detect_faces_insightface(img)
        return self._detect_faces_mock(img)
    
    def _detect_faces_mock(self, img: np.ndarray) -> List[Dict]:
        height, width = img.shape[:2]
        faces = []
        x = width // 4
        y = height // 4
        w = min(200, width // 2)
        h = min(240, height // 2)
        faces.append({
            'bbox': [max(0, x), max(0, y), min(width, x + w), min(height, y + h)],
            'confidence': 0.95,
            'nose_tip': None
        })
        return faces
    
    def _detect_faces_insightface(self, img: np.ndarray) -> List[Dict]:
        faces = self.analysis.get(img)
        print(f'[FaceRecognizerV2] 检测到 {len(faces)} 张人脸')
        result = []
        for face in faces:
            bbox = face.bbox.astype(int).tolist()
            print(f'[FaceRecognizerV2]   人脸 bbox={bbox} score={face.det_score:.2f}')
            embedding = face.embedding
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            nose_tip = None
            if hasattr(face, 'kps') and face.kps is not None and len(face.kps) >= 3:
                nose_tip = face.kps[2].tolist()
            result.append({
                'bbox': bbox,
                'confidence': float(face.det_score),
                'embedding': embedding,
                'nose_tip': nose_tip,
                'landmarks': face.kps if hasattr(face, 'kps') else None
            })
        return result
    
    def extract_descriptor(self, img: np.ndarray, bbox: Optional[List] = None) -> np.ndarray:
        if self.use_real_models:
            return self._extract_descriptor_insightface(img, bbox)
        return self._extract_descriptor_mock(img, bbox)
    
    def _extract_descriptor_mock(self, img: np.ndarray, bbox: Optional[List]) -> np.ndarray:
        if bbox is not None:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            face_img = img[y1:y2, x1:x2]
        else:
            face_img = img
        if face_img.size == 0:
            return np.random.randn(self.embedding_dim).astype(np.float32)
        descriptor = np.random.randn(self.embedding_dim).astype(np.float32)
        descriptor = descriptor / (np.linalg.norm(descriptor) + 1e-8)
        return descriptor
    
    def _extract_descriptor_insightface(self, img: np.ndarray, bbox: Optional[List]) -> np.ndarray:
        if bbox is not None:
            x1, y1, x2, y2 = [int(max(0, v)) for v in bbox]
            h, w = img.shape[:2]
            x1, y1 = min(x1, w - 1), min(y1, h - 1)
            x2, y2 = min(x2, w), min(y2, h)
            if x2 > x1 and y2 > y1:
                img = img[y1:y2, x1:x2]
        faces = self.analysis.get(img)
        if len(faces) > 0:
            return faces[0].embedding
        return np.zeros(self.embedding_dim, dtype=np.float32)
    
    def _check_dimension_match(self, stored_bytes: bytes, current_dim: int) -> bool:
        stored_dim = len(stored_bytes) // 4
        return stored_dim == current_dim
    
    def _crop_face(self, img: np.ndarray, bbox: List[int]) -> Optional[np.ndarray]:
        """裁剪人脸区域"""
        x1, y1, x2, y2 = [int(max(0, v)) for v in bbox]
        h, w = img.shape[:2]
        x1, y1 = min(x1, w - 1), min(y1, h - 1)
        x2, y2 = min(x2, w), min(y2, h)
        if x2 > x1 and y2 > y1:
            return img[y1:y2, x1:x2]
        return None
    
    def register_template(self, student_id: str, img_b64: str, 
                          bbox: Optional[List] = None) -> Dict:
        """
        注册人脸模板（支持多模板）
        Args:
            student_id: 学生 ID
            img_b64: 图像 base64
            bbox: 可选的人脸框
        Returns:
            注册结果
        """
        img = self.base64_to_numpy(img_b64)
        
        if bbox is None:
            faces = self.detect_faces(img)
            if not faces:
                return {"success": False, "error": "未检测到人脸"}
            bbox = faces[0]['bbox']
        
        # 提取特征
        feature = self.extract_descriptor(img, bbox)
        feature = feature / (np.linalg.norm(feature) + 1e-8)
        
        # 质量评估
        face_img = self._crop_face(img, bbox)
        quality_score = 0.8
        if face_img is not None:
            quality_result = self.quality_assessor.assess(face_img)
            quality_score = quality_result.overall
        
        # 使用 v2 多模板系统
        if self.use_v2_features and self.multi_matcher is not None:
            self.multi_matcher.add_template(student_id, feature, quality=quality_score)
            template_idx = self.multi_matcher.get_template_count(student_id) - 1
        else:
            # 向后兼容：单模板
            self.templates[student_id] = feature.tobytes()
            template_idx = 0
        
        print(f'[FaceRecognizerV2] 注册模板: student_id={student_id}, template_idx={template_idx}, quality={quality_score:.3f}')
        
        return {
            "success": True,
            "student_id": student_id,
            "template_idx": template_idx,
            "quality": quality_score
        }
    
    def load_students_from_dict(self, students_dict: Dict[str, bytes]):
        """
        从旧格式字典加载学生数据（向后兼容）
        Args:
            students_dict: {student_id: feature_bytes}
        """
        if not students_dict:
            return
        
        # 清空现有数据
        if self.use_v2_features and self.multi_matcher is not None:
            self.multi_matcher.clear()
        
        for student_id, stored_bytes in students_dict.items():
            if stored_bytes is None:
                continue
            
            # 恢复特征
            stored = np.frombuffer(stored_bytes, dtype=np.float32)
            stored = stored / (np.linalg.norm(stored) + 1e-8)
            
            if self.use_v2_features and self.multi_matcher is not None:
                self.multi_matcher.add_template(student_id, stored, quality=0.8)
            else:
                self.templates[student_id] = stored_bytes
        
        print(f'[FaceRecognizerV2] 从字典加载 {len(students_dict)} 个学生')
    
    def recognize_v2(self, img_b64: str, students_dict: Optional[Dict[str, bytes]] = None) -> Dict:
        """
        v2 增强版识别（支持多模板、FAISS、质量评估、增强活体检测）
        """
        img = self.base64_to_numpy(img_b64)
        faces = self.detect_faces(img)
        
        pool = get_liveness_pool()
        
        recognized_students = []
        all_liveness_flags = []
        liveness_details = []
        
        # 如果提供了旧格式字典，先加载到 v2 系统
        if students_dict and (self.use_v2_features and self.multi_matcher is not None):
            if self.multi_matcher.get_student_count() == 0:
                self.load_students_from_dict(students_dict)
        
        for idx, face in enumerate(faces):
            # 获取人脸图像区域
            bbox = face['bbox']
            face_img = self._crop_face(img, bbox)
            
            # 获取关键点
            landmarks = face.get('landmarks')
            nose_tip = face.get('nose_tip')
            
            # 使用增强版活体检测
            liveness_detector = pool.get_or_create(idx)
            
            face_live = False
            current_liveness_detail = {}
            
            if landmarks is not None:
                # 有完整关键点，使用增强检测
                liveness_result = liveness_detector.get_score(
                    face_img, landmarks, nose_tip=nose_tip, face_bbox=bbox
                )
                face_live = liveness_result.is_live
                
                # 保存详细信息
                current_liveness_detail = {
                    'nose_score': liveness_result.nose_score,
                    'blink_score': liveness_result.blink_score,
                    'classifier_score': liveness_result.classifier_score,
                    'overall_score': liveness_result.overall_score,
                    'blink_count': liveness_result.blink_count
                }
            
            liveness_details.append(current_liveness_detail)
            all_liveness_flags.append(face_live)
            
            if self.use_real_models and 'embedding' in face:
                descriptor = face['embedding']
            else:
                descriptor = self.extract_descriptor(img, face['bbox'])
            
            descriptor = descriptor / (np.linalg.norm(descriptor) + 1e-8)
            
            best_match = None
            max_cos_sim = 0.0
            
            # 使用 v2 多模板匹配
            if self.use_v2_features and self.multi_matcher is not None:
                match_result = self.multi_matcher.match(descriptor)
                if match_result is not None:
                    best_match = match_result.student_id
                    max_cos_sim = match_result.confidence
            else:
                # 向后兼容：旧的线性搜索
                if students_dict:
                    current_dim = len(descriptor)
                    for student_id, stored_desc in students_dict.items():
                        if stored_desc is None:
                            continue
                        if not self._check_dimension_match(stored_desc, current_dim):
                            continue
                        stored = np.frombuffer(stored_desc, dtype=np.float32)
                        stored = stored / (np.linalg.norm(stored) + 1e-8)
                        cos_sim = float(np.dot(descriptor, stored))
                        if cos_sim > 0.45 and cos_sim > max_cos_sim:
                            max_cos_sim = cos_sim
                            best_match = student_id
            
            if best_match is not None:
                result_detail = current_liveness_detail
                if not face_live:
                    print(f'[FaceRecognizerV2] face_{idx} 匹配到 student_id={best_match} 但活体检测未通过')
                    recognized_students.append({
                        'student_id': best_match,
                        'confidence': float(max_cos_sim),
                        'bbox': face['bbox'],
                        'liveness': False,
                        **result_detail
                    })
                    continue
                print(f'[FaceRecognizerV2] face_{idx} 匹配成功: student_id={best_match} (cos_sim={max_cos_sim:.4f})')
                recognized_students.append({
                    'student_id': best_match,
                    'confidence': float(max_cos_sim),
                    'bbox': face['bbox'],
                    'liveness': True,
                    **result_detail
                })
        
        any_live = any(all_liveness_flags) if all_liveness_flags else False
        
        return {
            'detected_faces': len(faces),
            'recognized': recognized_students,
            'liveness': any_live,
            'liveness_details': liveness_details
        }
    
    def recognize_with_tracking(self, img_b64: str, students_dict: Optional[Dict[str, bytes]] = None) -> Dict:
        """
        带追踪的识别接口（性能优化版本）
        使用人脸追踪减少重复计算，提高多人识别效率
        """
        img = self.base64_to_numpy(img_b64)
        faces = self.detect_faces(img)
        
        if not self.use_tracking or self.tracker is None:
            # 如果没有启用追踪，回退到普通识别
            return self.recognize_v2(img_b64, students_dict)
        
        # 收集检测框
        bboxes = [np.array(face['bbox']) for face in faces]
        embeddings = [face.get('embedding') for face in faces]
        
        # 更新追踪器
        active_tracks = self.tracker.update(bboxes, embeddings)
        
        # 获取需要识别的轨迹
        tracks_to_recognize = self.tracker.get_tracks_for_recognition()
        
        # 构建轨迹 ID 到检测框的映射
        track_to_face = {}
        for track in active_tracks:
            for idx, face in enumerate(faces):
                iou = self.tracker._iou(track.bbox, np.array(face['bbox']))
                if iou > 0.5:
                    track_to_face[track.track_id] = (track, face, idx)
                    break
        
        pool = get_liveness_pool()
        recognized_students = []
        all_liveness_flags = []
        liveness_details = []
        
        # 如果提供了旧格式字典，先加载到 v2 系统
        if students_dict and (self.use_v2_features and self.multi_matcher is not None):
            if self.multi_matcher.get_student_count() == 0:
                self.load_students_from_dict(students_dict)
        
        # 处理需要识别的轨迹
        for track in tracks_to_recognize:
            if track.track_id not in track_to_face:
                continue
            
            _, face, idx = track_to_face[track.track_id]
            bbox = face['bbox']
            face_img = self._crop_face(img, bbox)
            landmarks = face.get('landmarks')
            nose_tip = face.get('nose_tip')
            
            # 活体检测
            liveness_detector = pool.get_or_create(idx)
            face_live = False
            current_liveness_detail = {}
            
            if landmarks is not None:
                liveness_result = liveness_detector.get_score(
                    face_img, landmarks, nose_tip=nose_tip, face_bbox=bbox
                )
                face_live = liveness_result.is_live
                current_liveness_detail = {
                    'nose_score': liveness_result.nose_score,
                    'blink_score': liveness_result.blink_score,
                    'classifier_score': liveness_result.classifier_score,
                    'overall_score': liveness_result.overall_score,
                    'blink_count': liveness_result.blink_count
                }
            
            liveness_details.append(current_liveness_detail)
            all_liveness_flags.append(face_live)
            
            # 获取特征
            if self.use_real_models and 'embedding' in face:
                descriptor = face['embedding']
            else:
                descriptor = self.extract_descriptor(img, face['bbox'])
            
            descriptor = descriptor / (np.linalg.norm(descriptor) + 1e-8)
            
            best_match = None
            max_cos_sim = 0.0
            
            # 使用 v2 多模板匹配
            if self.use_v2_features and self.multi_matcher is not None:
                match_result = self.multi_matcher.match(descriptor)
                if match_result is not None:
                    best_match = match_result.student_id
                    max_cos_sim = match_result.confidence
            else:
                # 向后兼容：旧的线性搜索
                if students_dict:
                    current_dim = len(descriptor)
                    for student_id, stored_desc in students_dict.items():
                        if stored_desc is None:
                            continue
                        if not self._check_dimension_match(stored_desc, current_dim):
                            continue
                        stored = np.frombuffer(stored_desc, dtype=np.float32)
                        stored = stored / (np.linalg.norm(stored) + 1e-8)
                        cos_sim = float(np.dot(descriptor, stored))
                        if cos_sim > 0.45 and cos_sim > max_cos_sim:
                            max_cos_sim = cos_sim
                            best_match = student_id
            
            # 更新追踪器的识别结果
            if best_match:
                self.tracker.update_recognition_result(track.track_id, best_match, max_cos_sim)
        
        # 收集所有活跃轨迹的识别结果（包括缓存的）
        for track in active_tracks:
            if track.student_id:
                # 检查是否已签到
                is_signed = self.tracker.is_already_signed(track.student_id)
                
                recognized_students.append({
                    'track_id': track.track_id,
                    'student_id': track.student_id,
                    'confidence': track.confidence,
                    'bbox': track.bbox.tolist(),
                    'is_signed': is_signed,
                    'cached': (track.last_recognized_frame != self.tracker.frame_count),
                    'liveness': True
                })
        
        any_live = any(all_liveness_flags) if all_liveness_flags else False
        
        return {
            'detected_faces': len(faces),
            'recognized': recognized_students,
            'liveness': any_live,
            'liveness_details': liveness_details,
            'tracked_faces': [{'track_id': t.track_id, 'bbox': t.bbox.tolist()} for t in active_tracks],
            'tracker_stats': self.tracker.get_stats()
        }
    
    def mark_attendance(self, student_id: str):
        """
        标记学生已签到
        """
        if self.tracker:
            self.tracker.mark_signed(student_id)
    
    def reset_tracker(self):
        """
        重置追踪器（切换班级/场景时使用）
        """
        if self.tracker:
            self.tracker.reset()
    
    def recognize(self, img_b64: str, students_dict: Dict[str, bytes]) -> Dict:
        """
        向后兼容的识别接口
        """
        return self.recognize_v2(img_b64, students_dict)


# 单例模式
_face_recognizer_v2: Optional[FaceRecognizerV2] = None


def get_recognizer_v2(use_v2_features: bool = True) -> FaceRecognizerV2:
    """获取 v2 识别器单例"""
    global _face_recognizer_v2
    if _face_recognizer_v2 is None:
        _face_recognizer_v2 = FaceRecognizerV2(use_v2_features=use_v2_features)
    return _face_recognizer_v2


def get_recognizer() -> Any:
    """
    向后兼容接口 - 返回 v1 风格的识别器
    实际上返回 v2 识别器，保持 API 兼容
    """
    return get_recognizer_v2(use_v2_features=True)
