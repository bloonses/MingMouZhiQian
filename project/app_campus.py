# app_campus.py
# 校园网访问专用版本 - 让用户连接校园网即可使用系统

import os
import re
import secrets
import hashlib
import socket
import subprocess
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file, session, send_from_directory
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
from backblaze_b2_storage import BackblazeBackupManager
from dotenv import load_dotenv
import threading
import time

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
app.config['SESSION_COOKIE_SECURE'] = False  # 校园网内使用HTTP
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止JavaScript访问
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF保护
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传大小
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 静态文件缓存1年

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

    # 访问日志
    access_handler = RotatingFileHandler('logs/access.log', maxBytes=10000, backupCount=1)
    access_handler.setLevel(logging.INFO)
    access_formatter = logging.Formatter('[%(asctime)s] %(client_ip)s - %(path)s - %(user_agent)s')
    access_handler.setFormatter(access_formatter)
    app.logger.addHandler(access_handler)

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
                password_hash=generate_password_hash('Admin@12345'),
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
    return True

def sanitize_input(text):
    """清理输入"""
    if not text:
        return ""
    text = re.sub(r'[<>"\'&]', '', text)
    return text.strip()

# 网络工具函数
def get_local_ip():
    """获取本地IP地址"""
    try:
        # 获取本地IP地址
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return "127.0.0.1"

def get_network_info():
    """获取网络信息"""
    info = {
        'local_ip': get_local_ip(),
        'hostname': socket.gethostname(),
        'port': 5000,
        'access_urls': []
    }

    # 生成可能的访问URL
    local_ip = info['local_ip']

    # 校园网常见访问方式
    possible_urls = [
        f"http://{local_ip}:5000",
        f"http://{local_ip}:80",
        f"http://localhost:5000",
    ]

    # 尝试获取公网IP
    try:
        result = subprocess.run(['curl', '-s', 'ifconfig.me'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            public_ip = result.stdout.strip()
            possible_urls.append(f"http://{public_ip}:5000")
    except:
        pass

    info['access_urls'] = possible_urls
    return info

def generate_qr_code(url):
    """生成二维码"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # 转换为base64
        import io
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_base64 = base64.b64encode(buf.getvalue()).decode()

        return img_base64
    except Exception as e:
        app.logger.error(f"生成二维码失败: {e}")
        return None

# 主页 - 显示系统信息和访问方式
@app.route('/')
def home():
    """主页 - 显示访问方式和系统信息"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cloud_status = "已配置" if backup_manager else "未配置"
    cloud_status_class = "online" if backup_manager else "offline"
    cloud_status_text = "☁️ 云存储已连接" if backup_manager else "⚠️ 云存储未配置"

    # 获取网络信息
    network_info = get_network_info()

    return render_template('index.html',
                         cloud_status=cloud_status,
                         cloud_status_class=cloud_status_class,
                         cloud_status_text=cloud_status_text,
                         network_info=network_info,
                         access_urls=network_info['access_urls'],
                         class_count=0,  # 默认值，可以根据需要获取
                         student_count=0,  # 默认值，可以根据需要获取
                         today_attendance=0,  # 默认值，可以根据需要获取
                         attendance_rate=0,  # 默认值，可以根据需要获取
                         class_stats=[])  # 默认值，可以根据需要获取

# 系统信息页面
@app.route('/system-info')
def system_info():
    """系统信息页面"""
    network_info = get_network_info()

    # 生成二维码
    qr_code = generate_qr_code(network_info['access_urls'][0])

    return jsonify({
        'success': True,
        'network': network_info,
        'qr_code': qr_code,
        'system_time': datetime.now().isoformat(),
        'uptime': get_system_uptime(),
        'storage_status': get_storage_status()
    })

# 网络诊断页面
@app.route('/network-test')
def network_test():
    """网络诊断页面"""
    test_results = {
        'local_ip': get_local_ip(),
        'hostname': socket.gethostname(),
        'port_test': test_port_access(),
        'internet_access': test_internet_access(),
        'file_access': test_file_access(),
        'timestamp': datetime.now().isoformat()
    }

    return jsonify(test_results)

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

            # 记录访问日志
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

# 静态文件访问
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件访问"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        app.logger.error(f"静态文件访问失败: {e}")
        return jsonify({'success': False, 'message': '文件不存在'}), 404

# 视频流页面（用于人脸识别）
@app.route('/camera')
def camera():
    """摄像头页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('test_face_detection.html')

# 管理页面
@app.route('/admin')
def admin():
    """管理页面"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return render_template('admin.html')

# 学生管理
@app.route('/students')
def students():
    """学生管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    students = Student.query.all()
    return render_template('students.html', students=students)

# 课程管理
@app.route('/courses')
def courses():
    """课程管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

# 考勤记录
@app.route('/attendance')
def attendance():
    """考勤记录页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    attendances = Attendance.query.order_by(Attendance.check_in_time.desc()).limit(100).all()
    return render_template('attendance.html', attendances=attendances)

# 云存储功能接口（保持与之前相同的接口）
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

# 工具函数
def get_system_uptime():
    """获取系统运行时间"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_str = f"{uptime_seconds / 3600:.1f}小时"
        return uptime_str
    except:
        return "未知"

def get_storage_status():
    """获取存储状态"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent': (used / total) * 100
        }
    except:
        return None

def test_port_access():
    """测试端口访问"""
    try:
        # 测试本地端口是否可访问
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect(('localhost', 5000))
        sock.close()
        return True
    except:
        return False

def test_internet_access():
    """测试网络访问"""
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'],
                               capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def test_file_access():
    """测试文件访问"""
    try:
        test_file = 'test_access.txt'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except:
        return False

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
    print("🚀 启动校园网访问版本 - 人脸考勤系统")
    print("=" * 60)

    # 获取网络信息
    network_info = get_network_info()

    print("\n🌐 网络访问信息:")
    print(f"   本地IP: {network_info['local_ip']}")
    print(f"   主机名: {network_info['hostname']}")
    print(f"   端口: 5000")

    print("\n📱 访问地址:")
    for i, url in enumerate(network_info['access_urls'], 1):
        print(f"   {i}. {url}")

    print("\n📱 快速访问二维码:")
    print("   扫描二维码即可快速访问系统")

    print("\n🎯 使用说明:")
    print("   1. 确保防火墙允许5000端口访问")
    print("   2. 同一校园网内的设备可通过以上地址访问")
    print("   3. 如无法访问，请检查网络设置和防火墙")

    if backup_manager:
        print("\n☁️ 云存储状态:")
        print("   ✅ B2云存储已配置")
        print(f"   存储桶: {os.getenv('B2_BUCKET_NAME')}")
        print(f"   存储桶ID: {os.getenv('B2_BUCKET_ID')}")
        print("   提供商: Backblaze B2 (10GB永久免费)")
    else:
        print("\n⚠️  云存储状态:")
        print("   ❌ B2云存储配置失败")
        print("   请检查环境变量配置")

    print("\n🌐 可用接口:")
    print("   GET  /                    - 主页（显示访问方式）")
    print("   GET  /system-info         - 系统信息和二维码")
    print("   GET  /network-test        - 网络诊断")
    print("   GET  /login              - 登录")
    print("   GET  /register           - 注册")
    print("   GET  /camera             - 摄像头（人脸识别）")
    print("   GET  /students           - 学生管理")
    print("   GET  /courses            - 课程管理")
    print("   GET  /attendance         - 考勤记录")
    print("   GET  /admin              - 管理页面")
    print("   POST /backup/database     - 备份数据库")
    print("   POST /backup/student_faces - 备份人脸数据")
    print("   POST /backup/all          - 备份所有数据")
    print("   GET  /list/backups        - 列出备份")
    print("   GET  /cloud/config       - 云存储配置")

    print("\n🔐 安全特性:")
    print("   ✅ 用户认证和授权")
    print("   ✅ CSRF保护")
    print("   ✅ 输入验证")
    print("   ✅ 访问日志")
    print("   ✅ 会话管理")

    print("\n" + "=" * 60)
    print("🎉 系统启动完成! 校园网用户可以开始使用了!")
    print("=" * 60)

    # 初始化数据库
    init_db()

    # 启动应用 - 监听所有接口，允许校园网访问
    app.run(
        host='0.0.0.0',        # 监听所有网络接口
        port=5000,             # 使用5000端口
        debug=False,           # 生产环境关闭调试模式
        threaded=True          # 支持多线程
    )