
"""
明眸智签 v2.0 数据库迁移模块
功能：
- Student 表扩展，新增 face_templates_json 字段
- 自动迁移脚本（幂等）
- 向后兼容支持
"""

import json
import sqlite3
from sqlalchemy import inspect, text


class StudentTemplate:
    """学生人脸模板数据结构"""
    
    def __init__(self, 
                 embedding, 
                 quality=1.0, 
                 yaw=0.0, 
                 pitch=0.0, 
                 roll=0.0,
                 timestamp=None):
        self.embedding = embedding
        self.quality = quality
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll
        self.timestamp = timestamp
    
    def to_dict(self):
        """转换为字典，用于 JSON 存储"""
        import base64
        return {
            'embedding_b64': base64.b64encode(self.embedding).decode('utf-8'),
            'quality': float(self.quality),
            'yaw': float(self.yaw),
            'pitch': float(self.pitch),
            'roll': float(self.roll),
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建模板对象"""
        import base64
        return cls(
            embedding=base64.b64decode(data['embedding_b64']),
            quality=data.get('quality', 1.0),
            yaw=data.get('yaw', 0.0),
            pitch=data.get('pitch', 0.0),
            roll=data.get('roll', 0.0),
            timestamp=data.get('timestamp')
        )


class FaceTemplatesManager:
    """人脸模板管理类"""
    
    def __init__(self):
        self.templates = []
    
    def add_template(self, template):
        """添加一个模板"""
        self.templates.append(template)
    
    def to_json(self):
        """序列化为 JSON 字符串"""
        return json.dumps([t.to_dict() for t in self.templates], ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str):
        """从 JSON 字符串反序列化"""
        manager = cls()
        if json_str:
            try:
                data = json.loads(json_str)
                for item in data:
                    manager.add_template(StudentTemplate.from_dict(item))
            except Exception:
                pass
        return manager
    
    def get_main_template(self):
        """获取主模板（第一个或质量最高的）"""
        if not self.templates:
            return None
        # 返回质量最高的模板
        best = max(self.templates, key=lambda t: t.quality)
        return best.embedding


def migrate_database(db_session, db_engine):
    """
    执行数据库迁移（幂等操作）
    检查 face_templates_json 字段是否存在，不存在则添加
    同时将现有 face_descriptor 和 face_descriptor_512 转换为初始模板
    """
    inspector = inspect(db_engine)
    
    # 检查 student 表是否存在 face_templates_json 列
    columns = [c['name'] for c in inspector.get_columns('student')]
    
    if 'face_templates_json' not in columns:
        with db_engine.connect() as conn:
            # 添加新列
            conn.execute(text('ALTER TABLE student ADD COLUMN face_templates_json TEXT'))
            conn.commit()
        print('[DB Migration] 已添加 face_templates_json 列')
    
    # 处理现有数据：将旧的 face_descriptor 和 face_descriptor_512 迁移到新字段
    # 这里我们不在这里执行批量迁移，而是在读取时动态兼容
    print('[DB Migration] 数据库迁移完成')


def get_student_templates(student):
    """
    向后兼容的获取学生人脸模板
    优先使用 face_templates_json，不存在则从旧字段构建
    """
    if hasattr(student, 'face_templates_json') and student.face_templates_json:
        return FaceTemplatesManager.from_json(student.face_templates_json)
    
    # 向后兼容：从旧字段构建模板
    manager = FaceTemplatesManager()
    
    # 优先使用 512 维特征作为主模板
    if hasattr(student, 'face_descriptor_512') and student.face_descriptor_512:
        manager.add_template(StudentTemplate(
            embedding=student.face_descriptor_512,
            quality=1.0
        ))
    
    # 然后添加 128 维特征
    if hasattr(student, 'face_descriptor') and student.face_descriptor:
        manager.add_template(StudentTemplate(
            embedding=student.face_descriptor,
            quality=0.9
        ))
    
    return manager


def save_student_templates(student, templates_manager):
    """保存学生人脸模板"""
    if hasattr(student, 'face_templates_json'):
        student.face_templates_json = templates_manager.to_json()
    
    # 向后兼容：同时更新旧字段（保持主模板）
    main_embedding = templates_manager.get_main_template()
    if main_embedding:
        if hasattr(student, 'face_descriptor_512'):
            student.face_descriptor_512 = main_embedding
        if hasattr(student, 'face_descriptor') and len(main_embedding) == 128 * 4:
            student.face_descriptor = main_embedding


if __name__ == '__main__':
    print('明眸智签 v2.0 数据库迁移模块')
    print('请通过 app.py 初始化或调用 migrate_database() 函数执行迁移')

