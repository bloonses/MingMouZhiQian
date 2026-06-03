
"""
明眸智签 v2.0 数据库迁移测试
测试 TR-3.1: 迁移脚本可重复执行（幂等）
测试 TR-3.2: 旧数据库升级后数据不丢失
"""

import os
import tempfile
import shutil
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

# 导入迁移模块
from db_migration import (
    migrate_database,
    get_student_templates,
    save_student_templates,
    StudentTemplate,
    FaceTemplatesManager
)


def create_test_app(db_path):
    """创建测试 Flask 应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    return app


def create_legacy_database(db_path):
    """创建旧版数据库（无 face_templates_json 字段）"""
    app = create_test_app(db_path)
    db = SQLAlchemy(app)
    
    # 定义旧版 Student 模型（无新字段）
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(200), nullable=False)
        name = db.Column(db.String(100), nullable=False)
        role = db.Column(db.String(20), default='teacher')
    
    class Class(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    class Student(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        student_id = db.Column(db.String(50), nullable=False)
        class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
        face_descriptor = db.Column(db.LargeBinary)
        face_descriptor_512 = db.Column(db.LargeBinary)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        user = User(
            username='test_user',
            password_hash='test_hash',
            name='Test User'
        )
        db.session.add(user)
        db.session.commit()
        
        # 创建测试班级
        cls = Class(
            name='Test Class',
            user_id=user.id
        )
        db.session.add(cls)
        db.session.commit()
        
        # 创建测试学生数据（包含旧的人脸特征）
        test_descriptor = np.random.rand(128).astype(np.float32).tobytes()
        test_descriptor_512 = np.random.rand(512).astype(np.float32).tobytes()
        
        student1 = Student(
            name='张三',
            student_id='2024001',
            class_id=cls.id,
            face_descriptor=test_descriptor,
            face_descriptor_512=test_descriptor_512,
            user_id=user.id
        )
        
        student2 = Student(
            name='李四',
            student_id='2024002',
            class_id=cls.id,
            face_descriptor=test_descriptor,
            face_descriptor_512=None,
            user_id=user.id
        )
        
        db.session.add(student1)
        db.session.add(student2)
        db.session.commit()
        
        return app, db, Student


def test_tr_3_1_migration_idempotent():
    """
    测试 TR-3.1: 迁移脚本可重复执行（幂等）
    """
    print('[TR-3.1] 测试迁移脚本幂等性...')
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_idempotent.db')
    
    try:
        # 第一步：创建旧版数据库并首次迁移
        app, db, Student = create_legacy_database(db_path)
        
        with app.app_context():
            # 首次迁移
            migrate_database(db.session, db.engine)
            
            # 验证新字段已添加
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('student')]
            assert 'face_templates_json' in columns, '首次迁移后应该存在 face_templates_json 字段'
            print('[TR-3.1] ✓ 首次迁移成功，新字段已添加')
            
            # 第二次迁移（应该不报错）
            try:
                migrate_database(db.session, db.engine)
                print('[TR-3.1] ✓ 第二次迁移成功，无错误')
            except Exception as e:
                assert False, f'第二次迁移失败: {e}'
            
            # 第三次迁移（依然应该不报错）
            try:
                migrate_database(db.session, db.engine)
                print('[TR-3.1] ✓ 第三次迁移成功，无错误')
            except Exception as e:
                assert False, f'第三次迁移失败: {e}'
        
        print('[TR-3.1] ✅ 幂等性测试通过！\n')
        return True
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_tr_3_2_data_preservation():
    """
    测试 TR-3.2: 旧数据库升级后数据不丢失
    """
    print('[TR-3.2] 测试旧数据完整性...')
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_preservation.db')
    
    try:
        # 创建旧版数据库并记录原始数据
        app, db, Student = create_legacy_database(db_path)
        
        original_data = {}
        with app.app_context():
            students = Student.query.all()
            for s in students:
                original_data[s.id] = {
                    'name': s.name,
                    'student_id': s.student_id,
                    'face_descriptor': s.face_descriptor,
                    'face_descriptor_512': s.face_descriptor_512
                }
            print(f'[TR-3.2] 记录了 {len(original_data)} 个学生的原始数据')
        
        # 现在我们需要重新定义包含新字段的模型，以便测试
        # 创建新的应用实例
        app2 = create_test_app(db_path)
        db2 = SQLAlchemy(app2)
        
        class User2(db2.Model):
            __tablename__ = 'user'
            id = db2.Column(db2.Integer, primary_key=True)
            username = db2.Column(db2.String(80), unique=True, nullable=False)
            password_hash = db2.Column(db2.String(200), nullable=False)
            name = db2.Column(db2.String(100), nullable=False)
            role = db2.Column(db2.String(20), default='teacher')
        
        class Class2(db2.Model):
            __tablename__ = 'class'
            id = db2.Column(db2.Integer, primary_key=True)
            name = db2.Column(db2.String(100), nullable=False)
            user_id = db2.Column(db2.Integer, db2.ForeignKey('user.id'), nullable=False)
        
        class Student2(db2.Model):
            __tablename__ = 'student'
            id = db2.Column(db2.Integer, primary_key=True)
            name = db2.Column(db2.String(100), nullable=False)
            student_id = db2.Column(db2.String(50), nullable=False)
            class_id = db2.Column(db2.Integer, db2.ForeignKey('class.id'), nullable=False)
            face_descriptor = db2.Column(db2.LargeBinary)
            face_descriptor_512 = db2.Column(db2.LargeBinary)
            face_templates_json = db2.Column(db2.Text)  # 新字段
            user_id = db2.Column(db2.Integer, db2.ForeignKey('user.id'), nullable=False)
        
        with app2.app_context():
            # 执行迁移
            migrate_database(db2.session, db2.engine)
            
            # 验证数据完整性
            students_after = Student2.query.all()
            assert len(students_after) == len(original_data), '学生数量应该保持不变'
            
            for s in students_after:
                orig = original_data[s.id]
                assert s.name == orig['name'], f'学生 {s.id} 姓名不匹配'
                assert s.student_id == orig['student_id'], f'学生 {s.id} 学号不匹配'
                assert s.face_descriptor == orig['face_descriptor'], f'学生 {s.id} 128维特征不匹配'
                assert s.face_descriptor_512 == orig['face_descriptor_512'], f'学生 {s.id} 512维特征不匹配'
                print(f'[TR-3.2] ✓ 学生 {s.name} 数据完整')
            
            # 测试向后兼容：通过 get_student_templates 能正确获取旧数据
            print('[TR-3.2] 测试向后兼容读取...')
            for s in students_after:
                templates = get_student_templates(s)
                assert len(templates.templates) > 0, f'学生 {s.name} 应该能读取到模板'
                print(f'[TR-3.2] ✓ 学生 {s.name} 成功读取 {len(templates.templates)} 个模板')
                
                # 测试保存模板
                new_template = StudentTemplate(
                    embedding=np.random.rand(512).astype(np.float32).tobytes(),
                    quality=0.95
                )
                templates.add_template(new_template)
                save_student_templates(s, templates)
            
            db2.session.commit()
            print('[TR-3.2] ✓ 模板保存成功')
            
            # 再次验证旧字段仍然存在且正确
            students_final = Student2.query.all()
            for s in students_final:
                orig = original_data[s.id]
                # 验证旧字段没有被破坏（这里只验证非空的，因为保存时可能会更新）
                if orig['face_descriptor'] is not None:
                    assert s.face_descriptor is not None, f'学生 {s.name} face_descriptor 不应为 None'
                if orig['face_descriptor_512'] is not None:
                    assert s.face_descriptor_512 is not None, f'学生 {s.name} face_descriptor_512 不应为 None'
        
        print('[TR-3.2] ✅ 旧数据完整性测试通过！\n')
        return True
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('明眸智签 v2.0 - 数据库迁移测试')
    print('=' * 60)
    print()
    
    results = []
    
    try:
        result = test_tr_3_1_migration_idempotent()
        results.append(('TR-3.1', result))
    except Exception as e:
        print(f'[TR-3.1] ❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('TR-3.1', False))
    
    try:
        result = test_tr_3_2_data_preservation()
        results.append(('TR-3.2', result))
    except Exception as e:
        print(f'[TR-3.2] ❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('TR-3.2', False))
    
    print('=' * 60)
    print('测试总结:')
    for name, passed in results:
        status = '✅ 通过' if passed else '❌ 失败'
        print(f'  {name}: {status}')
    print('=' * 60)
    
    all_passed = all(r[1] for r in results)
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

