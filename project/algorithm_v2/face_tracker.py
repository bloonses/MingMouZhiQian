"""
明眸智签 v2.0 - 人脸追踪模块
功能：SORT 追踪器 + 结果缓存 + 批量推理支持
"""

import numpy as np
import time
from typing import List, Dict, Optional, Tuple


class TrackedFace:
    """被追踪的人脸"""
    def __init__(self, track_id: int, bbox: np.ndarray):
        self.track_id = track_id
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.last_seen = 0  # 已缺失帧数
        self.hits = 1  # 连续命中次数
        self.student_id: Optional[str] = None
        self.is_signed = False  # 是否已签到
        self.embedding: Optional[np.ndarray] = None  # 缓存的特征向量
        self.last_recognized_frame = -1  # 最后一次识别的帧号
        self.confidence: float = 0.0  # 识别置信度
        self.quality_score: float = 0.0  # 质量分数
        self.creation_time = time.time()  # 轨迹创建时间


class FaceTracker:
    """增强版人脸追踪器 - 支持 IoU 匹配、轨迹管理、签到缓存、批量推理"""
    
    def __init__(self, max_age: int = 5, min_hits: int = 3, 
                 iou_threshold: float = 0.3, cache_timeout: int = 300,
                 recognition_interval: int = 3):
        """
        Args:
            max_age: 最多容忍的缺失帧数
            min_hits: 连续命中次数才确认为有效轨迹
            iou_threshold: IoU 匹配阈值
            cache_timeout: 签到缓存超时时间（秒）
            recognition_interval: 识别间隔（每 N 帧识别一次）
        """
        self.tracks: Dict[int, TrackedFace] = {}
        self.next_id = 1
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        
        # 签到缓存：student_id -> (timestamp, is_signed)
        self.signed_cache: Dict[str, Tuple[float, bool]] = {}
        self.cache_timeout = cache_timeout  # 缓存超时时间（秒）
        
        # 帧计数器
        self.frame_count = 0
        
        # 检测频率控制：每 N 帧才进行一次完整识别
        self.recognition_interval = recognition_interval  # 默认每 3 帧识别一次
        self.tracking_only = False  # 是否仅追踪不识别
    
    def _iou(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算 IoU (Intersection over Union)"""
        a_x1, a_y1, a_x2, a_y2 = a
        b_x1, b_y1, b_x2, b_y2 = b
        
        inter_x1 = max(a_x1, b_x1)
        inter_y1 = max(a_y1, b_y1)
        inter_x2 = min(a_x2, b_x2)
        inter_y2 = min(a_y2, b_y2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        a_area = (a_x2 - a_x1) * (a_y2 - a_y1)
        b_area = (b_x2 - b_x1) * (b_y2 - b_y1)
        union_area = a_area + b_area - inter_area
        
        return inter_area / union_area
    
    def update(self, detections: List[np.ndarray], 
               embeddings: Optional[List[np.ndarray]] = None,
               quality_scores: Optional[List[float]] = None) -> List[TrackedFace]:
        """
        更新追踪
        Args:
            detections: 检测框列表，每个为 [x1,y1,x2,y2]
            embeddings: 可选的特征向量列表
            quality_scores: 可选的质量分数列表
        Returns:
            活跃的 TrackedFace 列表
        """
        self.frame_count += 1
        
        # 老化已有轨迹
        for track_id in list(self.tracks.keys()):
            self.tracks[track_id].last_seen += 1
            if self.tracks[track_id].last_seen > self.max_age:
                del self.tracks[track_id]
        
        # 匈牙利匹配（简化：贪心 IoU 匹配）
        matched = set()
        
        for det_idx, det in enumerate(detections):
            best_iou = 0.0
            best_id = None
            
            for track_id, track in self.tracks.items():
                if track_id in matched:
                    continue
                iou = self._iou(det, track.bbox)
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_id = track_id
            
            if best_id is not None:
                # 匹配到
                track = self.tracks[best_id]
                track.bbox = det
                track.last_seen = 0
                track.hits += 1
                
                # 更新特征（如果提供）
                if embeddings is not None and det_idx < len(embeddings):
                    track.embedding = embeddings[det_idx]
                if quality_scores is not None and det_idx < len(quality_scores):
                    track.quality_score = quality_scores[det_idx]
                
                matched.add(best_id)
            else:
                # 新轨迹
                new_track = TrackedFace(self.next_id, det)
                if embeddings is not None and det_idx < len(embeddings):
                    new_track.embedding = embeddings[det_idx]
                if quality_scores is not None and det_idx < len(quality_scores):
                    new_track.quality_score = quality_scores[det_idx]
                self.tracks[self.next_id] = new_track
                self.next_id += 1
        
        # 返回活跃轨迹
        active = []
        for track in self.tracks.values():
            if track.hits >= self.min_hits and track.last_seen == 0:
                active.append(track)
        return active
    
    def get_tracks_for_recognition(self) -> List[TrackedFace]:
        """
        获取需要进行识别的轨迹
        根据 recognition_interval 控制识别频率，减少计算量
        """
        if self.tracking_only:
            return []
        
        tracks_to_recognize = []
        for track in self.tracks.values():
            if (track.hits >= self.min_hits and 
                track.last_seen == 0 and
                (self.frame_count - track.last_recognized_frame) >= self.recognition_interval):
                tracks_to_recognize.append(track)
        return tracks_to_recognize
    
    def update_recognition_result(self, track_id: int, student_id: str, 
                                  confidence: float = 0.0):
        """
        更新轨迹的识别结果
        """
        if track_id in self.tracks:
            track = self.tracks[track_id]
            track.student_id = student_id
            track.confidence = confidence
            track.last_recognized_frame = self.frame_count
    
    def mark_signed(self, student_id: str):
        """标记学生已签到（加入缓存，带时间窗口）"""
        self.signed_cache[student_id] = (time.time(), True)
    
    def is_already_signed(self, student_id: str) -> bool:
        """检查是否已签到（考虑时间窗口）"""
        if student_id not in self.signed_cache:
            return False
        timestamp, is_signed = self.signed_cache[student_id]
        if time.time() - timestamp > self.cache_timeout:
            del self.signed_cache[student_id]
            return False
        return is_signed
    
    def cleanup_expired_cache(self):
        """清理过期的签到缓存"""
        current_time = time.time()
        expired = [sid for sid, (ts, _) in self.signed_cache.items() 
                   if current_time - ts > self.cache_timeout]
        for sid in expired:
            del self.signed_cache[sid]
    
    def get_active_tracks(self) -> List[TrackedFace]:
        """获取所有活跃轨迹"""
        return [track for track in self.tracks.values() 
                if track.hits >= self.min_hits and track.last_seen <= 1]
    
    def reset(self):
        """重置（切换班级/模式）"""
        self.tracks = {}
        self.next_id = 1
        self.signed_cache = {}
        self.frame_count = 0
    
    def get_stats(self) -> Dict:
        """获取追踪器统计信息"""
        active_count = len(self.get_active_tracks())
        total_tracks = len(self.tracks)
        signed_count = len([sid for sid in self.signed_cache 
                           if self.is_already_signed(sid)])
        return {
            'total_tracks': total_tracks,
            'active_tracks': active_count,
            'signed_students': signed_count,
            'frame_count': self.frame_count,
            'next_id': self.next_id
        }


class BatchFaceRecognizer:
    """批量人脸识别处理器 - 结合追踪器优化性能"""
    
    def __init__(self, tracker: Optional[FaceTracker] = None):
        self.tracker = tracker or FaceTracker()
        self.enable_tracking = True
    
    def process_frame(self, img, detector_func, extractor_func, 
                     matcher_func, liveness_func=None):
        """
        处理单帧图像，支持批量推理和追踪
        Args:
            img: 输入图像
            detector_func: 人脸检测函数
            extractor_func: 特征提取函数
            matcher_func: 匹配函数
            liveness_func: 活体检测函数（可选）
        Returns:
            处理结果
        """
        # 1. 检测人脸
        faces = detector_func(img)
        if not faces:
            return {
                'detected_faces': 0,
                'recognized': [],
                'tracked_faces': [],
                'stats': self.tracker.get_stats()
            }
        
        # 提取检测框、特征等
        bboxes = [face['bbox'] for face in faces]
        bboxes_np = [np.array(bbox) for bbox in bboxes]
        
        # 2. 获取需要识别的轨迹
        if self.enable_tracking:
            # 更新追踪
            tracked_faces = self.tracker.update(bboxes_np)
            
            # 获取需要识别的轨迹
            tracks_to_recognize = self.tracker.get_tracks_for_recognition()
            
            if not tracks_to_recognize:
                # 仅返回追踪结果，不进行新识别
                recognized = []
                for track in tracked_faces:
                    if track.student_id:
                        recognized.append({
                            'track_id': track.track_id,
                            'student_id': track.student_id,
                            'confidence': track.confidence,
                            'bbox': track.bbox.tolist(),
                            'is_signed': self.tracker.is_already_signed(track.student_id),
                            'cached': True
                        })
                return {
                    'detected_faces': len(faces),
                    'recognized': recognized,
                    'tracked_faces': [{'track_id': t.track_id, 'bbox': t.bbox.tolist()} 
                                     for t in tracked_faces],
                    'stats': self.tracker.get_stats()
                }
        else:
            tracked_faces = []
        
        # 3. 批量特征提取
        embeddings = []
        for face in faces:
            if 'embedding' in face:
                embeddings.append(face['embedding'])
            else:
                emb = extractor_func(img, face['bbox'])
                embeddings.append(emb)
        
        # 4. 批量匹配
        recognized = []
        for idx, (face, emb) in enumerate(zip(faces, embeddings)):
            # 活体检测
            is_live = True
            if liveness_func:
                is_live = liveness_func(img, face)
            
            if not is_live:
                continue
            
            # 匹配
            match_result = matcher_func(emb)
            if match_result:
                student_id = match_result.get('student_id')
                confidence = match_result.get('confidence', 0.0)
                
                # 更新追踪器中的识别结果
                if self.enable_tracking:
                    # 找到对应的轨迹
                    for track in tracked_faces:
                        if self.tracker._iou(track.bbox, np.array(face['bbox'])) > 0.5:
                            self.tracker.update_recognition_result(track.track_id, student_id, confidence)
                            break
                
                # 检查是否已签到
                is_signed = self.tracker.is_already_signed(student_id)
                
                recognized.append({
                    'track_id': None,  # 后续会填充
                    'student_id': student_id,
                    'confidence': confidence,
                    'bbox': face['bbox'],
                    'is_signed': is_signed,
                    'cached': False
                })
        
        return {
            'detected_faces': len(faces),
            'recognized': recognized,
            'tracked_faces': [{'track_id': t.track_id, 'bbox': t.bbox.tolist()} 
                             for t in tracked_faces],
            'stats': self.tracker.get_stats()
        }
    
    def mark_attendance(self, student_id: str):
        """标记签到"""
        self.tracker.mark_signed(student_id)
    
    def reset(self):
        """重置"""
        self.tracker.reset()
