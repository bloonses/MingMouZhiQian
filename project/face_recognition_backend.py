import os
import base64
import time
import cv2
import numpy as np
import ssl

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


class LivenessTracker:
    def __init__(self):
        self.nose_history = []
        self.max_history = 25
        self.min_frames = 6
        self.movement_threshold = 10

    def update(self, nose_tip):
        self.nose_history.append({
            'x': float(nose_tip[0]),
            'y': float(nose_tip[1]),
            'time': time.time()
        })
        if len(self.nose_history) > self.max_history:
            self.nose_history = self.nose_history[-self.max_history:]

    def is_live(self):
        if len(self.nose_history) < self.min_frames:
            return False
        recent = self.nose_history[-self.min_frames:]
        y_values = [p['y'] for p in recent]
        x_values = [p['x'] for p in recent]
        y_range = max(y_values) - min(y_values)
        x_range = max(x_values) - min(x_values)
        return y_range > self.movement_threshold or x_range > self.movement_threshold

    def get_nose_count(self):
        return len(self.nose_history)

    def reset(self):
        self.nose_history = []


_liveness_tracker = LivenessTracker()


def get_liveness_tracker():
    return _liveness_tracker


class FaceRecognizer:
    def __init__(self, use_gpu=False):
        self.use_gpu = use_gpu
        self.use_real_models = False
        self.detector = None
        self.recognizer = None
        self.embedding_dim = 128
        self._init_insightface()
    
    def _init_insightface(self):
        try:
            import insightface
            print('[FaceRecognizer] 正在初始化 InsightFace...')

            project_insightface = os.path.join(os.path.dirname(__file__), '.insightface')

            candidate_roots = [
                project_insightface,
                os.path.expanduser('~/.insightface'),
            ]

            self.analysis = None
            last_error = None

            for root in candidate_roots:
                try:
                    print(f'[FaceRecognizer] 尝试加载模型 from: {root}')

                    buffalo_path = os.path.join(root, 'models', 'buffalo_l')
                    if os.path.exists(buffalo_path) and len(os.listdir(buffalo_path)) > 0:
                        print(f'[FaceRecognizer] 找到本地模型文件，直接加载...')

                    self.analysis = insightface.app.FaceAnalysis(
                        name='buffalo_l',
                        root=root,
                        providers=['CPUExecutionProvider'] if not self.use_gpu else ['CUDAExecutionProvider', 'CPUExecutionProvider']
                    )
                    self.analysis.prepare(ctx_id=0 if self.use_gpu else -1, det_size=(640, 640))
                    print(f'[FaceRecognizer] 成功从 {root} 加载模型')
                    break
                except Exception as e:
                    last_error = e
                    print(f'[FaceRecognizer] 加载失败 from {root}: {e}')
                    continue

            if self.analysis is None:
                raise last_error or Exception('所有路径都加载失败')

            self.embedding_dim = 512
            self.use_real_models = True
            print('[FaceRecognizer] InsightFace 模型初始化成功')
        except Exception as e:
            print('[FaceRecognizer] InsightFace 加载失败，降级到模拟模式:', str(e))
            self.embedding_dim = 128
            self._init_mock()
    
    def _init_mock(self):
        self.use_real_models = False
    
    @staticmethod
    def base64_to_numpy(image_b64):
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        image_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    
    @staticmethod
    def numpy_to_base64(img):
        _, buffer = cv2.imencode('.jpg', img)
        return base64.b64encode(buffer).decode('utf-8')
    
    def detect_faces(self, img):
        if self.use_real_models:
            return self._detect_faces_insightface(img)
        return self._detect_faces_mock(img)
    
    def _detect_faces_mock(self, img):
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
    
    def _detect_faces_insightface(self, img):
        faces = self.analysis.get(img)
        print(f'[FaceRecognizer] 检测到 {len(faces)} 张人脸')
        result = []
        for face in faces:
            bbox = face.bbox.astype(int).tolist()
            print(f'[FaceRecognizer]   人脸 bbox={bbox} score={face.det_score:.2f}')
            embedding = face.embedding
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            nose_tip = None
            if hasattr(face, 'kps') and face.kps is not None and len(face.kps) >= 3:
                nose_tip = face.kps[2].tolist()
            result.append({
                'bbox': bbox,
                'confidence': float(face.det_score),
                'embedding': embedding,
                'nose_tip': nose_tip
            })
        return result
    
    def extract_descriptor(self, img, bbox=None):
        if self.use_real_models:
            return self._extract_descriptor_insightface(img, bbox)
        return self._extract_descriptor_mock(img, bbox)
    
    def _extract_descriptor_mock(self, img, bbox):
        if bbox is not None:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            face_img = img[y1:y2, x1:x2]
        else:
            face_img = img
        if face_img.size == 0:
            return np.random.randn(128).astype(np.float32)
        face_img = cv2.resize(face_img, (112, 112))
        descriptor = np.mean(face_img, axis=(0, 1)) / 255.0
        descriptor = np.tile(descriptor, (43,))[:128].astype(np.float32)
        descriptor = descriptor / (np.linalg.norm(descriptor) + 1e-8)
        return descriptor
    
    def _extract_descriptor_insightface(self, img, bbox):
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
    
    def _check_dimension_match(self, stored_bytes, current_dim):
        stored_dim = len(stored_bytes) // 4
        return stored_dim == current_dim
    
    def recognize(self, img_b64, students_dict):
        img = self.base64_to_numpy(img_b64)
        faces = self.detect_faces(img)
        
        tracker = get_liveness_tracker()
        liveness_ok = False
        nose_count = 0
        
        if faces and faces[0].get('nose_tip'):
            tracker.update(faces[0]['nose_tip'])
            nose_count = tracker.get_nose_count()
            liveness_ok = tracker.is_live()
            print(f'[Recognize] 活体检测: nose_frames={nose_count}, liveness={liveness_ok}')
        
        recognized_students = []
        
        for face in faces:
            if self.use_real_models and 'embedding' in face:
                descriptor = face['embedding']
            else:
                descriptor = self.extract_descriptor(img, face['bbox'])
            
            descriptor = descriptor / (np.linalg.norm(descriptor) + 1e-8)
            current_dim = len(descriptor)
            max_cos_sim = -1.0
            best_match = None
            
            for student_id, stored_desc in students_dict.items():
                if stored_desc is None:
                    continue
                if not self._check_dimension_match(stored_desc, current_dim):
                    continue
                stored = np.frombuffer(stored_desc, dtype=np.float32)
                stored = stored / (np.linalg.norm(stored) + 1e-8)
                cos_sim = float(np.dot(descriptor, stored))
                distance = float(np.linalg.norm(descriptor - stored))
                print(f'[Recognize] student_id={student_id} cos_sim={cos_sim:.4f} distance={distance:.4f}')
                
                if cos_sim > 0.45 and cos_sim > max_cos_sim:
                    max_cos_sim = cos_sim
                    best_match = student_id
            
            if best_match is not None:
                if not liveness_ok:
                    print(f'[Recognize] 匹配到 student_id={best_match} 但活体检测未通过')
                    continue
                print(f'[Recognize] 匹配成功: student_id={best_match} (cos_sim={max_cos_sim:.4f})')
                recognized_students.append({
                    'student_id': best_match,
                    'confidence': float(max_cos_sim),
                    'bbox': face['bbox']
                })
        
        return {
            'detected_faces': len(faces),
            'recognized': recognized_students,
            'liveness': liveness_ok,
            'nose_frames': nose_count
        }


# 单例模式
_face_recognizer = None


def get_recognizer():
    global _face_recognizer
    if _face_recognizer is None:
        _face_recognizer = FaceRecognizer()
    return _face_recognizer
