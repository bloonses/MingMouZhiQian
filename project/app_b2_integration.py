# app_b2_integration.py
# B2云存储完整集成示例

import os
import json
from flask import Flask, jsonify, request
from backblaze_b2_storage import BackblazeB2Manager, BackblazeBackupManager
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 初始化B2云存储
def init_b2_storage():
    """初始化B2云存储"""
    try:
        config = {
            'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': os.getenv('B2_BUCKET_NAME'),
            'bucket_id': os.getenv('B2_BUCKET_ID'),
            'download_url': os.getenv('B2_DOWNLOAD_URL', 'https://f004.backblazeb2.com/file')
        }

        # 初始化存储管理器
        storage_manager = BackblazeB2Manager(config)

        # 初始化备份管理器
        backup_manager = BackblazeBackupManager(config)

        return storage_manager, backup_manager
    except Exception as e:
        print(f"B2存储初始化失败: {e}")
        return None, None

# 初始化B2服务
storage_manager, backup_manager = init_b2_storage()

@app.route('/')
def home():
    """主页"""
    status = "已配置" if storage_manager and backup_manager else "未配置"
    return f"人脸考勤系统 - B2云存储{status} (10GB永久免费)"

@app.route('/cloud/status')
def cloud_status():
    """获取云存储状态"""
    if not storage_manager or not backup_manager:
        return jsonify({
            'success': False,
            'message': 'B2云存储服务未初始化'
        })

    try:
        # 获取存储桶信息
        bucket_info = storage_manager.get_bucket_info()

        # 获取备份状态
        backup_status = backup_manager.get_backup_status()

        return jsonify({
            'success': True,
            'message': 'B2云存储连接正常',
            'storage': {
                'bucket_name': bucket_info['bucketName'],
                'bucket_id': bucket_info['bucketId'],
                'bucket_type': bucket_info['bucketType']
            },
            'backup': backup_status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取状态失败: {e}'
        })

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
        }
    }
    return jsonify(config_info)

@app.route('/backup/database', methods=['POST'])
def backup_database():
    """备份数据库"""
    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        # 检查数据库文件是否存在
        db_file = 'attendance.db'
        if not os.path.exists(db_file):
            return jsonify({'success': False, 'message': '数据库文件不存在'})

        success = backup_manager.backup_database(db_file)

        if success:
            return jsonify({'success': True, 'message': '数据库备份成功'})
        else:
            return jsonify({'success': False, 'message': '数据库备份失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/backup/student_faces', methods=['POST'])
def backup_student_faces():
    """备份学生人脸数据"""
    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        # 检查人脸数据目录是否存在
        faces_dir = 'static/faces'
        if not os.path.exists(faces_dir):
            return jsonify({'success': False, 'message': '人脸数据目录不存在'})

        success = backup_manager.backup_student_faces(faces_dir)

        if success:
            return jsonify({'success': True, 'message': '人脸数据备份成功'})
        else:
            return jsonify({'success': False, 'message': '人脸数据备份失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/backup/all', methods=['POST'])
def backup_all():
    """备份所有数据"""
    results = {
        'database': False,
        'student_faces': False,
        'message': ''
    }

    try:
        # 备份数据库
        db_file = 'attendance.db'
        if os.path.exists(db_file):
            db_success = backup_manager.backup_database(db_file)
            results['database'] = db_success
            if db_success:
                results['message'] += '数据库备份成功。'
            else:
                results['message'] += '数据库备份失败。'
        else:
            results['message'] += '数据库文件不存在。'

        # 备份人脸数据
        faces_dir = 'static/faces'
        if os.path.exists(faces_dir):
            faces_success = backup_manager.backup_student_faces(faces_dir)
            results['student_faces'] = faces_success
            if faces_success:
                results['message'] += '人脸数据备份成功。'
            else:
                results['message'] += '人脸数据备份失败。'
        else:
            results['message'] += '人脸数据目录不存在。'

        success = results['database'] or results['student_faces']
        return jsonify({
            'success': success,
            'results': results
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/list/backups')
def list_backups():
    """列出所有备份"""
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
        return jsonify({'success': False, 'message': f'获取备份列表失败: {e}'})

@app.route('/delete/backup', methods=['POST'])
def delete_backup():
    """删除备份"""
    if not backup_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        data = request.get_json()
        backup_name = data.get('backup_name')

        if not backup_name:
            return jsonify({'success': False, 'message': '请提供备份名称'})

        # 删除备份文件
        success = backup_manager.b2_manager.delete_file(backup_name)

        if success:
            return jsonify({'success': True, 'message': f'备份 {backup_name} 删除成功'})
        else:
            return jsonify({'success': False, 'message': f'备份 {backup_name} 删除失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {e}'})

@app.route('/upload/file', methods=['POST'])
def upload_file():
    """上传文件到B2"""
    if not storage_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        data = request.get_json()
        file_path = data.get('file_path')
        remote_path = data.get('remote_path')

        if not file_path or not remote_path:
            return jsonify({'success': False, 'message': '请提供文件路径和远程路径'})

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'})

        success = storage_manager.upload_file(file_path, remote_path)

        if success:
            return jsonify({'success': True, 'message': f'文件上传成功: {remote_path}'})
        else:
            return jsonify({'success': False, 'message': f'文件上传失败: {remote_path}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {e}'})

@app.route('/download/file', methods=['POST'])
def download_file():
    """从B2下载文件"""
    if not storage_manager:
        return jsonify({'success': False, 'message': 'B2云存储服务不可用'})

    try:
        data = request.get_json()
        remote_path = data.get('remote_path')
        local_path = data.get('local_path')

        if not remote_path or not local_path:
            return jsonify({'success': False, 'message': '请提供远程路径和本地路径'})

        success = storage_manager.download_file(remote_path, local_path)

        if success:
            return jsonify({'success': True, 'message': f'文件下载成功: {local_path}'})
        else:
            return jsonify({'success': False, 'message': f'文件下载失败: {remote_path}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {e}'})

@app.route('/health')
def health_check():
    """健康检查"""
    if storage_manager and backup_manager:
        try:
            # 简单的连接测试
            bucket_info = storage_manager.get_bucket_info()
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'storage': bucket_info['bucketName']
            })
        except:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': 'B2连接失败'
            })
    else:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': 'B2服务未初始化'
        })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500

if __name__ == '__main__':
    print("🚀 启动人脸考勤系统 - B2云存储集成")
    print("=" * 60)

    if storage_manager and backup_manager:
        print("✅ B2云存储已配置")
        print(f"   存储桶: {os.getenv('B2_BUCKET_NAME')}")
        print(f   存储桶ID: {os.getenv('B2_BUCKET_ID')}")
        print("   提供商: Backblaze B2 (10GB永久免费)")
    else:
        print("❌ B2云存储配置失败")
        print("请检查环境变量配置")

    print("\n🌐 可用接口:")
    print("   GET  /                    - 主页")
    print("   GET  /cloud/status        - 云存储状态")
    print("   GET  /cloud/config        - 云存储配置")
    print("   GET  /health              - 健康检查")
    print("   POST /backup/database     - 备份数据库")
    print("   POST /backup/student_faces - 备份人脸数据")
    print("   POST /backup/all          - 备份所有数据")
    print("   GET  /list/backups        - 列出备份")
    print("   POST /delete/backup       - 删除备份")
    print("   POST /upload/file         - 上传文件")
    print("   POST /download/file       - 下载文件")

    print("\n📊 数据:")
    print("   当前预估: 215MB")
    print("   1年预测: 2.58GB")
    print("   5年预测: 12.9GB")
    print("   免费限额: 10GB")

    print("\n💡 使用示例:")
    print("   curl http://localhost:5000/cloud/status")
    print("   curl -X POST http://localhost:5000/backup/database")
    print("   curl -X POST http://localhost:5000/backup/all")

    print("\n" + "=" * 60)
    print("🎉 系统启动完成! 开始使用B2云存储吧!")
    print("=" * 60)

    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)