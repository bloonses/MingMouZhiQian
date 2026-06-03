"""
明眸智签 v2.0 - API v2 模块
提供增强版人脸识别 API 端点，支持多模板、FAISS 索引、质量评估和增强活体检测
"""

import os
import base64
import numpy as np
from datetime import date
from typing import Dict, List, Optional, Any
from flask import jsonify, request, session

# 导入 v2 识别器
from .face_recognition_backend_v2 import get_recognizer_v2, FaceRecognizerV2
from .liveness_enhanced import get_liveness_pool
from .multi_template_matcher import MultiTemplateMatcher
from .faiss_index import FAISS_AVAILABLE


def require_login(f):
    """登录验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '未登录'})
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id():
    """获取当前用户 ID"""
    return session.get('user_id')


# ============================================================
# V2 API 端点
# ============================================================

@require_login
def recognize_v2():
    """
    增强版人脸识别 API
    POST /api/recognize_v2
    
    请求体:
    {
        "class_id": int,           # 班级 ID
        "course_id": int,          # 课程 ID (可选)
        "image": str,              # base64 编码的图像
        "use_tracking": bool      # 是否使用追踪模式 (可选, 默认 True)
    }
    
    返回:
    {
        "success": bool,
        "results": [...],           # 识别结果列表
        "detected_faces": int,      # 检测到的人脸数
        "liveness": bool,           # 是否有活体通过
        "liveness_details": [...],  # 活体分数详情
        "tracked_faces": [...],     # 追踪的人脸信息 (可选)
        "tracker_stats": {...}      # 追踪器统计 (可选)
    }
    """
    try:
        from app import db, Student, Attendance
        
        user_id = get_current_user_id()
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'})
        
        class_id = data.get('class_id')
        course_id = data.get('course_id')
        image_b64 = data.get('image')
        use_tracking = data.get('use_tracking', True)
        
        if not class_id or not image_b64:
            return jsonify({'success': False, 'error': '缺少必要参数: class_id 或 image'})
        
        # 加载班级学生特征
        students = Student.query.filter_by(class_id=class_id, user_id=user_id).all()
        students_dict = {
            str(s.id): s.face_descriptor_512
            for s in students if s.face_descriptor_512
        }
        
        if not students_dict:
            return jsonify({
                'success': False,
                'error': '班级无已录入人脸的学生（需重新采集人脸以启用后端识别）'
            })
        
        # 获取 v2 识别器
        recognizer = get_recognizer_v2(use_v2_features=True)
        
        # 选择识别模式
        if use_tracking:
            result = recognizer.recognize_with_tracking(image_b64, students_dict)
        else:
            result = recognizer.recognize_v2(image_b64, students_dict)
        
        recognized = result.get('recognized', [])
        face_count = result.get('detected_faces', 0)
        liveness_ok = result.get('liveness', False)
        liveness_details = result.get('liveness_details', [])
        
        # 处理识别结果
        results = []
        matched_ids = set()
        
        for idx, match in enumerate(recognized):
            student_id = match['student_id']
            matched_student = Student.query.filter_by(
                id=int(student_id), user_id=user_id
            ).first()
            
            if not matched_student:
                results.append({
                    'student_id': student_id,
                    'student_name': 'Unknown',
                    'checked_in': False,
                    'message': 'Student not found',
                    'bbox': match.get('bbox'),
                    'confidence': match.get('confidence', 0),
                    'liveness': match.get('liveness', False)
                })
                continue
            
            # 检查是否已签到
            today = date.today()
            existing = Attendance.query.filter(
                Attendance.student_id == matched_student.id,
                Attendance.user_id == user_id,
                db.func.date(Attendance.check_in_time) == today
            ).first()
            
            is_live = match.get('liveness', False)
            
            if existing:
                results.append({
                    'student_id': matched_student.id,
                    'student_name': matched_student.name,
                    'checked_in': False,
                    'already_attended': True,
                    'message': f'{matched_student.name} 今日已签到',
                    'bbox': match.get('bbox'),
                    'confidence': match.get('confidence', 0),
                    'liveness': is_live
                })
                matched_ids.add(matched_student.id)
                continue
            
            if not is_live:
                results.append({
                    'student_id': matched_student.id,
                    'student_name': matched_student.name,
                    'checked_in': False,
                    'message': f'{matched_student.name} 活体检测未通过',
                    'bbox': match.get('bbox'),
                    'confidence': match.get('confidence', 0),
                    'liveness': False
                })
                continue
            
            # 执行签到
            attendance = Attendance(
                student_id=matched_student.id,
                class_id=class_id,
                course_id=course_id,
                method='face_v2',
                user_id=user_id
            )
            db.session.add(attendance)
            db.session.commit()
            
            results.append({
                'student_id': matched_student.id,
                'student_name': matched_student.name,
                'checked_in': True,
                'message': f'{matched_student.name} 签到成功',
                'bbox': match.get('bbox'),
                'confidence': match.get('confidence', 0),
                'liveness': True
            })
            matched_ids.add(matched_student.id)
        
        # 构建响应
        response = {
            'success': True,
            'results': results,
            'detected_faces': face_count,
            'liveness': liveness_ok,
            'liveness_details': liveness_details,
            'matched_count': len(results),
            'signed_count': sum(1 for r in results if r.get('checked_in'))
        }
        
        # 如果使用追踪模式，添加追踪信息
        if use_tracking and 'tracked_faces' in result:
            response['tracked_faces'] = result['tracked_faces']
            response['tracker_stats'] = result.get('tracker_stats', {})
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        print(f'[API_v2/recognize_v2] 错误: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'识别失败: {str(e)}'})


@require_login
def get_face_template(student_id: int):
    """
    获取学生的人脸模板
    GET /api/face_templates/<student_id>
    
    返回:
    {
        "success": bool,
        "student_id": int,
        "has_128d": bool,          # 是否有 128 维特征
        "has_512d": bool,           # 是否有 512 维特征
        "template_count": int,      # V2 多模板数量
        "quality_score": float,     # 质量分数 (如有)
    }
    """
    try:
        from app import Student
        
        user_id = get_current_user_id()
        
        student = Student.query.filter_by(id=student_id, user_id=user_id).first()
        if not student:
            return jsonify({'success': False, 'error': '学生不存在'})
        
        # 检查特征类型
        has_128d = student.face_descriptor is not None
        has_512d = student.face_descriptor_512 is not None
        
        # 获取 v2 识别器的模板信息
        recognizer = get_recognizer_v2()
        template_count = 0
        quality_score = None
        
        if recognizer.multi_matcher:
            template_count = recognizer.multi_matcher.get_template_count(str(student_id))
        
        return jsonify({
            'success': True,
            'student_id': student.id,
            'student_name': student.name,
            'has_128d': has_128d,
            'has_512d': has_512d,
            'template_count': template_count,
            'quality_score': quality_score
        })
        
    except Exception as e:
        print(f'[API_v2/get_face_template] 错误: {e}')
        return jsonify({'success': False, 'error': f'获取模板失败: {str(e)}'})


@require_login
def add_face_template():
    """
    添加人脸模板
    POST /api/face_templates
    
    请求体:
    {
        "student_id": int,
        "image": str,              # base64 编码的图像
        "bbox": [x1, y1, x2, y2]   # 可选，人脸框
    }
    
    返回:
    {
        "success": bool,
        "student_id": int,
        "template_idx": int,       # 模板索引
        "quality": float           # 质量分数
    }
    """
    try:
        from app import Student, db
        
        user_id = get_current_user_id()
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'})
        
        student_id = data.get('student_id')
        image_b64 = data.get('image')
        bbox = data.get('bbox')
        
        if not student_id or not image_b64:
            return jsonify({'success': False, 'error': '缺少必要参数: student_id 或 image'})
        
        student = Student.query.filter_by(id=student_id, user_id=user_id).first()
        if not student:
            return jsonify({'success': False, 'error': '学生不存在'})
        
        # 使用 v2 识别器注册模板
        recognizer = get_recognizer_v2()
        
        result = recognizer.register_template(
            student_id=str(student_id),
            img_b64=image_b64,
            bbox=bbox
        )
        
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', '注册失败')})
        
        # 同时更新数据库中的 512 维特征
        img = recognizer.base64_to_numpy(image_b64)
        faces = recognizer.detect_faces(img)
        
        if faces:
            embedding = faces[0].get('embedding')
            if embedding is not None:
                student.face_descriptor_512 = embedding.astype(np.float32).tobytes()
                db.session.commit()
        
        return jsonify({
            'success': True,
            'student_id': student_id,
            'student_name': student.name,
            'template_idx': result.get('template_idx', 0),
            'quality': result.get('quality', 0)
        })
        
    except Exception as e:
        import traceback
        print(f'[API_v2/add_face_template] 错误: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'添加模板失败: {str(e)}'})


@require_login
def delete_face_template(student_id: int):
    """
    删除学生的所有人脸模板
    DELETE /api/face_templates/<student_id>
    
    返回:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        from app import Student
        
        user_id = get_current_user_id()
        
        student = Student.query.filter_by(id=student_id, user_id=user_id).first()
        if not student:
            return jsonify({'success': False, 'error': '学生不存在'})
        
        # 从 v2 识别器中删除模板
        recognizer = get_recognizer_v2()
        
        if recognizer.multi_matcher:
            recognizer.multi_matcher.remove_student(str(student_id))
        
        # 清除数据库特征
        student.face_descriptor = None
        student.face_descriptor_512 = None
        from app import db
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已删除学生 {student.name} 的所有人脸模板'
        })
        
    except Exception as e:
        print(f'[API_v2/delete_face_template] 错误: {e}')
        return jsonify({'success': False, 'error': f'删除模板失败: {str(e)}'})


@require_login
def rebuild_faiss_index():
    """
    重建 FAISS 索引
    POST /api/rebuild_index
    
    请求体:
    {
        "class_id": int,           # 班级 ID (可选，不填则重建所有)
    }
    
    返回:
    {
        "success": bool,
        "indexed_count": int,       # 索引的学生数
        "faiss_available": bool,    # FAISS 是否可用
        "message": str
    }
    """
    try:
        from app import Student, db
        
        user_id = get_current_user_id()
        data = request.json or {}
        class_id = data.get('class_id')
        
        # 获取学生数据
        if class_id:
            students = Student.query.filter_by(
                class_id=class_id, user_id=user_id
            ).all()
        else:
            students = Student.query.filter_by(user_id=user_id).all()
        
        # 收集有效的 512 维特征
        students_dict = {}
        for s in students:
            if s.face_descriptor_512:
                students_dict[str(s.id)] = s.face_descriptor_512
        
        # 获取 v2 识别器并重建索引
        recognizer = get_recognizer_v2()
        
        if recognizer.multi_matcher:
            recognizer.multi_matcher.clear()
            
            for student_id, desc_bytes in students_dict.items():
                desc = np.frombuffer(desc_bytes, dtype=np.float32)
                desc = desc / (np.linalg.norm(desc) + 1e-8)
                recognizer.multi_matcher.add_template(student_id, desc, quality=0.8)
        
        return jsonify({
            'success': True,
            'indexed_count': len(students_dict),
            'total_students': len(students),
            'faiss_available': FAISS_AVAILABLE,
            'message': f'索引重建完成，共索引 {len(students_dict)} 个学生模板'
        })
        
    except Exception as e:
        print(f'[API_v2/rebuild_index] 错误: {e}')
        return jsonify({'success': False, 'error': f'重建索引失败: {str(e)}'})


@require_login
def get_liveness_score_detail():
    """
    获取活体分数详情
    POST /api/liveness_score
    
    请求体:
    {
        "image": str,              # base64 编码的图像
        "face_idx": int            # 人脸索引 (可选, 默认 0)
    }
    
    返回:
    {
        "success": bool,
        "is_live": bool,
        "nose_score": float,        # 鼻尖移动分数
        "blink_score": float,       # 眨眼分数
        "classifier_score": float,  # 分类器分数
        "overall_score": float,     # 综合分数
        "blink_count": int,         # 检测到的眨眼次数
        "details": {...}            # 详细分析结果
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'})
        
        image_b64 = data.get('image')
        face_idx = data.get('face_idx', 0)
        
        if not image_b64:
            return jsonify({'success': False, 'error': '缺少 image 参数'})
        
        # 使用 v2 识别器
        recognizer = get_recognizer_v2()
        img = recognizer.base64_to_numpy(image_b64)
        
        # 检测人脸
        faces = recognizer.detect_faces(img)
        
        if not faces or face_idx >= len(faces):
            return jsonify({
                'success': False,
                'error': f'未检测到人脸或索引 {face_idx} 超出范围'
            })
        
        face = faces[face_idx]
        bbox = face['bbox']
        face_img = recognizer._crop_face(img, bbox)
        landmarks = face.get('landmarks')
        nose_tip = face.get('nose_tip')
        
        if landmarks is None:
            return jsonify({
                'success': False,
                'error': '无法获取人脸关键点，请确保使用真实 InsightFace 模型'
            })
        
        # 获取活体检测器
        pool = get_liveness_pool()
        detector = pool.get_or_create(face_idx)
        
        # 执行活体检测
        liveness_result = detector.get_score(
            face_img, landmarks, nose_tip=nose_tip, face_bbox=bbox
        )
        
        return jsonify({
            'success': True,
            'is_live': liveness_result.is_live,
            'nose_score': liveness_result.nose_score,
            'blink_score': liveness_result.blink_score,
            'classifier_score': liveness_result.classifier_score,
            'overall_score': liveness_result.overall_score,
            'blink_count': liveness_result.blink_count,
            'nose_movement': getattr(liveness_result, 'nose_movement', None),
            'eye_distances': getattr(liveness_result, 'eye_distances', []),
            'bbox': bbox,
            'confidence': face.get('confidence', 0)
        })
        
    except Exception as e:
        import traceback
        print(f'[API_v2/liveness_score] 错误: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'活体检测失败: {str(e)}'})


@require_login
def reset_liveness_tracker():
    """
    重置活体追踪器
    POST /api/liveness_reset
    
    返回:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        pool = get_liveness_pool()
        pool.reset()
        
        recognizer = get_recognizer_v2()
        if recognizer.tracker:
            recognizer.tracker.reset()
        
        return jsonify({
            'success': True,
            'message': '活体追踪器已重置'
        })
        
    except Exception as e:
        print(f'[API_v2/reset_liveness] 错误: {e}')
        return jsonify({'success': False, 'error': f'重置失败: {str(e)}'})


@require_login
def get_v2_status():
    """
    获取 V2 系统状态
    GET /api/v2_status
    
    返回:
    {
        "success": bool,
        "recognizer_initialized": bool,
        "use_real_models": bool,
        "faiss_available": bool,
        "embedding_dim": int,
        "template_stats": {...}
    }
    """
    try:
        recognizer = get_recognizer_v2()
        
        template_stats = {}
        if recognizer.multi_matcher:
            template_stats = {
                'total_templates': recognizer.multi_matcher.get_total_templates(),
                'student_count': recognizer.multi_matcher.get_student_count(),
                'faiss_indexed': recognizer.faiss_index is not None
            }
        
        return jsonify({
            'success': True,
            'recognizer_initialized': True,
            'use_real_models': recognizer.use_real_models,
            'faiss_available': FAISS_AVAILABLE,
            'embedding_dim': recognizer.embedding_dim,
            'use_v2_features': recognizer.use_v2_features,
            'use_tracking': recognizer.use_tracking,
            'template_stats': template_stats
        })
        
    except Exception as e:
        print(f'[API_v2/status] 错误: {e}')
        return jsonify({'success': False, 'error': f'获取状态失败: {str(e)}'})


# ============================================================
# API 路由注册
# ============================================================

def register_v2_routes(app):
    """
    注册 V2 API 路由到 Flask app
    """
    # 增强版识别
    app.add_url_rule(
        '/api/recognize_v2',
        'recognize_v2',
        recognize_v2,
        methods=['POST']
    )
    
    # 获取学生模板
    app.add_url_rule(
        '/api/face_templates/<int:student_id>',
        'get_face_template',
        get_face_template,
        methods=['GET']
    )
    
    # 添加模板
    app.add_url_rule(
        '/api/face_templates',
        'add_face_template',
        add_face_template,
        methods=['POST']
    )
    
    # 删除模板
    app.add_url_rule(
        '/api/face_templates/<int:student_id>',
        'delete_face_template',
        delete_face_template,
        methods=['DELETE']
    )
    
    # 重建 FAISS 索引
    app.add_url_rule(
        '/api/rebuild_index',
        'rebuild_faiss_index',
        rebuild_faiss_index,
        methods=['POST']
    )
    
    # 活体分数详情
    app.add_url_rule(
        '/api/liveness_score',
        'get_liveness_score_detail',
        get_liveness_score_detail,
        methods=['POST']
    )
    
    # 重置活体追踪器
    app.add_url_rule(
        '/api/liveness_reset',
        'reset_liveness_tracker',
        reset_liveness_tracker,
        methods=['POST']
    )
    
    # V2 系统状态
    app.add_url_rule(
        '/api/v2_status',
        'get_v2_status',
        get_v2_status,
        methods=['GET']
    )
    
    print('[API_v2] V2 API 路由注册完成')