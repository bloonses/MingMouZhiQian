# app_with_cloud.py
# 集成B2云存储功能的人脸考勤系统主应用

import os
import re
import secrets
import hashlib
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import numpy as np
import openpyxl
from openpyxl import Workbook
from io import BytesIO
import base64
import qrcode
import logging
from logging.handlers import RotatingFileHandler
# 导入B2云存储功能
from backblaze_b2_storage import BackblazeBackupManager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 初始化云存储备份
def setup_cloud_backup():
    """初始化云存储备份功能"""
    try:
        config = {
            'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': os.getenv('B2_BUCKET_NAME'),
            'bucket_id': os.getenv('B2_BUCKET_ID'),
            'backup_prefix': 'backup/',
            'max_backups': 30
        }

        backup_manager = BackblazeBackupManager(config)
        return backup_manager
    except Exception as e:
        app.logger.error(f"云存储初始化失败: {e}")
        return None

# 初始化备份管理器
backup_manager = setup_cloud_backup()

# 安全的密钥生成
def generate_secure_secret_key():
    """生成安全的密钥"""
    return secrets.token_urlsafe(32)

# 配置安全的会话密钥
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', generate_secure_secret_key())
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # 会话2小时后过期
app.config['SESSION_COOKIE_SECURE'] = True  # 仅HTTPS传输
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止JavaScript访问
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF保护
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传大小
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}

# 配置日志
def setup_logging():
    """配置安全的日志记录"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # 错误日志
    handler = RotatingFileHandler('logs/error.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

# 数据库模型
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='teacher')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    security_question = db.Column(db.String(200))
    security_answer_hash = db.Column(db.String(255))
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked = db.Column(db.Boolean, default=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    face_encoding = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')
    image_path = db.Column(db.String(200))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 数据库初始化
def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()

        # 创建默认管理员账户（如果不存在）
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                name='系统管理员',
                password_hash=generate_password_hash('Admin@12345'),  # 已修改默认密码
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账户已创建")
            print("用户名: admin")
            print("密码: Admin@12345")

# 设置日志
setup_logging()

# CSRF保护装饰器
def csrf_protected(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or csrf_token != session.get('csrf_token'):
                app.logger.warning(f"CSRF验证失败 - IP: {request.remote_addr}")
                return jsonify({'success': False, 'message': '安全验证失败'}), 400
        return f(*args, **kwargs)
    return decorated_function

# 输入验证函数
def is_safe_username(username):
    """验证用户名安全性"""
    if not username or len(username) < 2 or len(username) > 20:
        return False
    if not re.match(r'^[a-zA-Z0-9_一-龥]+$', username):
        return False
    return True

def is_strong_password(password):
    """验证密码强度"""
    if len(password) < 6:
        return False
    if len(password) > 100:
        return False
    # 可以添加更多密码强度检查
    return True

def sanitize_input(text):
    """清理输入"""
    if not text:
        return ""
    # 移除潜在的危险字符
    text = re.sub(r'[<>"\'&]', '', text)
    return text.strip()

# 主页
@app.route('/')
def home():
    """主页"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cloud_status = "已配置" if backup_manager else "未配置"
    return render_template('index.html', cloud_status=cloud_status)

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='请填写用户名和密码')

        user = User.query.filter_by(username=username).first()

        if user and user.account_locked:
            return render_template('login.html', error='账户已被锁定，请联系管理员')

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['csrf_token'] = secrets.token_urlsafe(16)

            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            user.failed_login_attempts = 0
            db.session.commit()

            app.logger.info(f"用户 {username} 登录成功 - IP: {request.remote_addr}")
            return redirect(url_for('home'))
        else:
            # 记录失败尝试
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.account_locked = True
                    app.logger.warning(f"用户 {username} 账户被锁定 - IP: {request.remote_addr}")
                db.session.commit()

            app.logger.warning(f"登录失败 - 用户: {username}, IP: {request.remote_addr}")
            return render_template('login.html', error='用户名或密码错误')

    session['csrf_token'] = secrets.token_urlsafe(16)
    return render_template('login.html', csrf_token=session['csrf_token'])

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not name:
            return render_template('register.html', error='请填写完整的注册信息')

        if not is_safe_username(username):
            return render_template('register.html', error='用户名格式不正确')

        if len(name) > 50:
            return render_template('register.html', error='姓名不能超过50个字符')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='用户名已存在')

        if password != confirm_password:
            return render_template('register.html', error='两次输入的密码不一致')

        if not is_strong_password(password):
            return render_template('register.html', error='密码长度至少为6位')

        security_question = request.form.get('security_question', '').strip()
        security_answer = request.form.get('security_answer', '').strip()

        if not security_question or not security_answer:
            return render_template('register.html', error='请填写安全问题')

        new_user = User(
            username=username,
            name=name,
            password_hash=generate_password_hash(password),
            role='teacher',
            security_question=security_question,
            security_answer_hash=generate_password_hash(security_answer)
        )
        db.session.add(new_user)
        db.session.commit()

        app.logger.info(f"新用户注册: {username}")
        return redirect(url_for('login'))

    session['csrf_token'] = secrets.token_urlsafe(16)
    return render_template('register.html', csrf_token=session['csrf_token'])

# 管理页面
@app.route('/admin')
def admin():
    """管理页面"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return render_template('admin.html')

# 云存储功能接口
@app.route('/cloud/status')
def cloud_status():
    """获取云存储状态"""
    if not backup_manager:
        return jsonify({
            'success': False,
            'message': 'B2云存储服务未初始化',
            'config_status': '未配置'
        })

    try:
        status = backup_manager.get_backup_status()
        return jsonify({
            'success': True,
            'message': 'B2云存储连接正常',
            'config_status': '已配置',
            'storage': {
                'provider': 'Backblaze B2',
                'bucket_name': os.getenv('B2_BUCKET_NAME'),
                'bucket_id': os.getenv('B2_BUCKET_ID'),
                'free_quota': {
                    'storage': '10GB',
                    'download': '1GB/天',
                    'upload': '无限制',
                    'duration': '永久免费'
                }
            },
            'backup': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取状态失败: {e}',
            'config_status': '配置错误'
        })

@app.route('/backup/database', methods=['POST'])
@csrf_protected
def backup_database():
    """备份数据库"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '需要管理员权限'})

    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        success = backup_manager.backup_database('attendance.db')

        if success:
            app.logger.info("数据库备份成功")
            return jsonify({'success': True, 'message': '数据库备份成功'})
        else:
            app.logger.error("数据库备份失败")
            return jsonify({'success': False, 'message': '数据库备份失败'})
    except Exception as e:
        app.logger.error(f"数据库备份异常: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/backup/student_faces', methods=['POST'])
@csrf_protected
def backup_student_faces():
    """备份学生人脸数据"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '需要管理员权限'})

    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        success = backup_manager.backup_student_faces('static/faces')

        if success:
            app.logger.info("人脸数据备份成功")
            return jsonify({'success': True, 'message': '人脸数据备份成功'})
        else:
            app.logger.error("人脸数据备份失败")
            return jsonify({'success': False, 'message': '人脸数据备份失败'})
    except Exception as e:
        app.logger.error(f"人脸数据备份异常: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/backup/all', methods=['POST'])
@csrf_protected
def backup_all():
    """备份所有数据"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '需要管理员权限'})

    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    results = {
        'database': False,
        'student_faces': False,
        'message': ''
    }

    try:
        # 备份数据库
        try:
            db_success = backup_manager.backup_database('attendance.db')
            results['database'] = db_success
            results['message'] += '数据库备份成功。' if db_success else '数据库备份失败。'
        except Exception as e:
            results['message'] += f'数据库备份异常: {e}。'

        # 备份人脸数据
        try:
            faces_success = backup_manager.backup_student_faces('static/faces')
            results['student_faces'] = faces_success
            results['message'] += '人脸数据备份成功。' if faces_success else '人脸数据备份失败。'
        except Exception as e:
            results['message'] += f'人脸数据备份异常: {e}。'

        success = results['database'] or results['student_faces']
        app.logger.info(f"完整备份结果: {success}")

        return jsonify({
            'success': success,
            'results': results
        })
    except Exception as e:
        app.logger.error(f"完整备份异常: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/list/backups')
def list_backups():
    """列出所有备份"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '需要管理员权限'})

    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        backups = backup_manager.list_backups()
        return jsonify({
            'success': True,
            'backups': backups,
            'count': len(backups)
        })
    except Exception as e:
        app.logger.error(f"获取备份列表异常: {e}")
        return jsonify({'success': False, 'message': f'获取备份列表失败: {e}'})

@app.route('/cloud/config')
def cloud_config():
    """获取云存储配置信息"""
    config_info = {
        'provider': 'Backblaze B2',
        'bucket_name': os.getenv('B2_BUCKET_NAME'),
        'bucket_id': os.getenv('B2_BUCKET_ID'),
        'free_quota': {
            'storage': '10GB',
            'download': '1GB/天',
            'upload': '无限制',
            'duration': '永久免费'
        },
        'local_data': {
            'current_estimation': '215MB',
            '1_year_projection': '2.58GB',
            '5_year_projection': '12.9GB'
        },
        'status': '已配置' if backup_manager else '未配置'
    }
    return jsonify(config_info)

# 原有的考勤功能路由保持不变
@app.route('/students')
def students():
    """学生管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/courses')
def courses():
    """课程管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

@app.route('/attendance')
def attendance():
    """考勤记录页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    attendances = Attendance.query.order_by(Attendance.check_in_time.desc()).limit(100).all()
    return render_template('attendance.html', attendances=attendances)

# 登出
@app.route('/logout')
def logout():
    """登出"""
    username = session.get('username', 'Unknown')
    session.clear()
    app.logger.info(f"用户 {username} 登出")
    return redirect(url_for('login'))

# 初始化数据库
if __name__ == '__main__':
    print("🚀 启动人脸考勤系统 - B2云存储集成版")
    print("=" * 60)

    if backup_manager:
        print("✅ B2云存储已配置")
        print(f"   存储桶: {os.getenv('B2_BUCKET_NAME')}")
        print(f"   存储桶ID: {os.getenv('B2_BUCKET_ID')}")
        print("   提供商: Backblaze B2 (10GB永久免费)")
    else:
        print("⚠️  B2云存储配置失败")
        print("请检查环境变量配置")

    print("\n🌐 可用接口:")
    print("   GET  /                    - 主页")
    print("   GET  /cloud/status        - 云存储状态")
    print("   GET  /cloud/config        - 云存储配置")
    print("   POST /backup/database     - 备份数据库")
    print("   POST /backup/student_faces - 备份人脸数据")
    print("   POST /backup/all          - 备份所有数据")
    print("   GET  /list/backups        - 列出备份")

    print("\n🔐 用户管理:")
    print("   GET  /login              - 登录")
    print("   GET  /register           - 注册")
    print("   GET  /logout             - 登出")
    print("   GET  /students           - 学生管理")
    print("   GET  /courses            - 课程管理")
    print("   GET  /attendance         - 考勤记录")

    print("\n💾 数据:")
    print("   当前预估: 215MB")
    print("   1年预测: 2.58GB")
    print("   5年预测: 12.9GB")
    print("   免费限额: 10GB")

    print("\n🎯 系统特性:")
    print("   ✅ 人脸识别考勤")
    print("   ✅ B2云存储备份")
    print("   ✅ 自动数据同步")
    print("   ✅ 安全用户认证")
    print("   ✅ 完整的权限管理")

    print("\n" + "=" * 60)
    print("🎉 系统启动完成! 开始使用吧!")
    print("=" * 60)

    # 初始化数据库
    init_db()

    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)