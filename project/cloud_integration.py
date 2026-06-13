"""
云存储集成模块 - 将云存储功能集成到主应用中
提供自动备份、数据同步等功能
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from cloud_storage import CloudStorageManager, CloudBackupManager, setup_cloud_storage

# 创建云存储蓝图
cloud_bp = Blueprint('cloud', __name__, url_prefix='/cloud')

# 配置日志
logger = logging.getLogger(__name__)

# 云存储配置
CLOUD_CONFIG = None
STORAGE_MANAGER = None
BACKUP_MANAGER = None


def init_cloud_storage(config_path='cloud_config.json'):
    """
    初始化云存储功能

    Args:
        config_path: 配置文件路径
    """
    global CLOUD_CONFIG, STORAGE_MANAGER, BACKUP_MANAGER

    try:
        # 加载配置文件
        from cloud_config import CloudStorageConfig
        CLOUD_CONFIG = CloudStorageConfig.load_config(config_path)

        if not CLOUD_CONFIG:
            logger.warning("云存储配置未找到，将使用默认配置")
            CLOUD_CONFIG = CloudStorageConfig.get_config('aws_s3')

        # 初始化存储管理器
        STORAGE_MANAGER = setup_cloud_storage(CLOUD_CONFIG['provider'], CLOUD_CONFIG['config'])

        # 初始化备份管理器
        BACKUP_MANAGER = CloudBackupManager(CLOUD_CONFIG['provider'], CLOUD_CONFIG['config'])

        logger.info(f"云存储功能初始化成功 - 使用 {CLOUD_CONFIG['provider']}")

    except Exception as e:
        logger.error(f"云存储初始化失败: {e}")
        raise


@cloud_bp.route('/status', methods=['GET'])
def get_cloud_status():
    """获取云存储状态"""
    try:
        if not STORAGE_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        # 检查连接状态
        try:
            # 尝试列出文件来检查连接
            files = STORAGE_MANAGER.list_files()
            return jsonify({
                'success': True,
                'status': 'connected',
                'provider': CLOUD_CONFIG['provider'],
                'bucket_name': CLOUD_CONFIG['bucket_name'],
                'file_count': len(files),
                'last_check': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'status': 'connected',
                'provider': CLOUD_CONFIG['provider'],
                'bucket_name': CLOUD_CONFIG['bucket_name'],
                'file_count': 0,
                'last_check': datetime.now().isoformat(),
                'message': f'连接正常，但检查文件列表时出错: {str(e)}'
            })

    except Exception as e:
        logger.error(f"获取云存储状态失败: {e}")
        return jsonify({'success': False, 'message': f'获取状态失败: {str(e)}'})


@cloud_bp.route('/backup/database', methods=['POST'])
def backup_database():
    """备份数据库到云存储"""
    try:
        if not BACKUP_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        # 获取数据库路径
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'attendance.db')

        # 如果是SQLite URI，提取实际路径
        if 'sqlite:///' in db_path:
            db_path = db_path.replace('sqlite:///', '')

        if not os.path.exists(db_path):
            return jsonify({'success': False, 'message': '数据库文件不存在'})

        # 执行备份
        success = BACKUP_MANAGER.backup_database(db_path)

        if success:
            return jsonify({
                'success': True,
                'message': '数据库备份成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'message': '数据库备份失败'})

    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {str(e)}'})


@cloud_bp.route('/backup/student_faces', methods=['POST'])
def backup_student_faces():
    """备份学生人脸数据到云存储"""
    try:
        if not BACKUP_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        # 获取人脸数据目录
        faces_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static'), 'faces')

        if not os.path.exists(faces_dir):
            return jsonify({'success': False, 'message': '人脸数据目录不存在'})

        # 执行备份
        success = BACKUP_MANAGER.backup_student_faces(faces_dir)

        if success:
            return jsonify({
                'success': True,
                'message': '学生人脸数据备份成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'message': '学生人脸数据备份失败'})

    except Exception as e:
        logger.error(f"学生人脸数据备份失败: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {str(e)}'})


@cloud_bp.route('/backup/all', methods=['POST'])
def backup_all():
    """备份所有数据到云存储"""
    try:
        if not BACKUP_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        results = {}

        # 备份数据库
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'attendance.db')
        if 'sqlite:///' in db_path:
            db_path = db_path.replace('sqlite:///', '')

        if os.path.exists(db_path):
            db_success = BACKUP_MANAGER.backup_database(db_path)
            results['database'] = {'success': db_success, 'timestamp': datetime.now().isoformat()}
        else:
            results['database'] = {'success': False, 'message': '数据库文件不存在'}

        # 备份学生人脸数据
        faces_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static'), 'faces')
        if os.path.exists(faces_dir):
            faces_success = BACKUP_MANAGER.backup_student_faces(faces_dir)
            results['student_faces'] = {'success': faces_success, 'timestamp': datetime.now().isoformat()}
        else:
            results['student_faces'] = {'success': False, 'message': '人脸数据目录不存在'}

        # 检查整体备份结果
        all_success = all(result['success'] for result in results.values())

        return jsonify({
            'success': all_success,
            'message': '所有数据备份完成' if all_success else '部分数据备份失败',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"完整备份失败: {e}")
        return jsonify({'success': False, 'message': f'备份失败: {str(e)}'})


@cloud_bp.route('/restore/database', methods=['POST'])
def restore_database():
    """从云存储恢复数据库"""
    try:
        if not STORAGE_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        data = request.json
        backup_name = data.get('backup_name')

        if not backup_name:
            return jsonify({'success': False, 'message': '请指定要恢复的备份文件'})

        # 生成临时恢复路径
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        restore_path = f'restore_database_{timestamp}.db'

        # 从云存储下载备份
        success = STORAGE_MANAGER.download_file(f'backup/{backup_name}', restore_path)

        if success:
            return jsonify({
                'success': True,
                'message': f'数据库恢复成功，文件保存为: {restore_path}',
                'restore_path': restore_path,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'message': '数据库恢复失败'})

    except Exception as e:
        logger.error(f"数据库恢复失败: {e}")
        return jsonify({'success': False, 'message': f'恢复失败: {str(e)}'})


@cloud_bp.route('/list/backups', methods=['GET'])
def list_backups():
    """列出所有备份"""
    try:
        if not BACKUP_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        backups = BACKUP_MANAGER.list_backups()

        return jsonify({
            'success': True,
            'backups': backups,
            'count': len(backups),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"列出备份失败: {e}")
        return jsonify({'success': False, 'message': f'列出备份失败: {str(e)}'})


@cloud_bp.route('/delete/backup', methods=['POST'])
def delete_backup():
    """删除指定备份"""
    try:
        if not STORAGE_MANAGER:
            return jsonify({'success': False, 'message': '云存储未初始化'})

        data = request.json
        backup_name = data.get('backup_name')

        if not backup_name:
            return jsonify({'success': False, 'message': '请指定要删除的备份文件'})

        success = STORAGE_MANAGER.delete_file(f'backup/{backup_name}')

        if success:
            return jsonify({
                'success': True,
                'message': f'备份 {backup_name} 删除成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'message': '备份删除失败'})

    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        return jsonify({'success': False, 'message': f'删除备份失败: {str(e)}'})


@cloud_bp.route('/config', methods=['GET'])
def get_cloud_config():
    """获取云存储配置"""
    try:
        if not CLOUD_CONFIG:
            return jsonify({'success': False, 'message': '云存储未配置'})

        # 隐藏敏感信息
        safe_config = CLOUD_CONFIG.copy()
        if 'config' in safe_config:
            config = safe_config['config']
            # 隐藏敏感字段
            for sensitive_field in ['access_key_id', 'secret_access_key', 'account_key', 'connection_string']:
                if sensitive_field in config:
                    config[sensitive_field] = '***masked***'

        return jsonify({
            'success': True,
            'config': safe_config,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({'success': False, 'message': f'获取配置失败: {str(e)}'})


@cloud_bp.route('/config', methods=['POST'])
def update_cloud_config():
    """更新云存储配置"""
    try:
        data = request.json
        provider = data.get('provider', 'aws_s3')

        # 更新配置
        from cloud_config import CloudStorageConfig
        CLOUD_CONFIG = CloudStorageConfig.get_config(provider)

        # 重新初始化云存储
        STORAGE_MANAGER = setup_cloud_storage(CLOUD_CONFIG['provider'], CLOUD_CONFIG['config'])
        BACKUP_MANAGER = CloudBackupManager(CLOUD_CONFIG['provider'], CLOUD_CONFIG['config'])

        return jsonify({
            'success': True,
            'message': '云存储配置更新成功',
            'provider': provider,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"更新云存储配置失败: {e}")
        return jsonify({'success': False, 'message': f'更新配置失败: {str(e)}'})


@cloud_bp.route('/test_connection', methods=['POST'])
def test_connection():
    """测试云存储连接"""
    try:
        data = request.json
        provider = data.get('provider', 'aws_s3')
        config = data.get('config', {})

        # 测试连接
        test_storage = setup_cloud_storage(provider, config)

        # 尝试列出文件
        files = test_storage.list_files()

        return jsonify({
            'success': True,
            'message': '云存储连接测试成功',
            'provider': provider,
            'file_count': len(files),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"云存储连接测试失败: {e}")
        return jsonify({
            'success': False,
            'message': f'连接测试失败: {str(e)}',
            'provider': provider
        })


# 自动备份任务
def schedule_auto_backup():
    """调度自动备份任务"""
    try:
        if BACKUP_MANAGER and BACKUP_MANAGER.auto_backup:
            # 执行完整备份
            BACKUP_MANAGER.backup_database('attendance.db')
            BACKUP_MANAGER.backup_student_faces('static/faces')

            logger.info("自动备份任务完成")

    except Exception as e:
        logger.error(f"自动备份任务失败: {e}")


# 健康检查任务
def health_check():
    """健康检查"""
    try:
        if STORAGE_MANAGER:
            # 检查连接状态
            files = STORAGE_MANAGER.list_files()
            logger.info(f"云存储健康检查通过，当前文件数量: {len(files)}")

    except Exception as e:
        logger.error(f"云存储健康检查失败: {e}")


# 注册云存储路由
def register_cloud_routes(app):
    """注册云存储路由"""
    app.register_blueprint(cloud_bp)

    # 添加初始化钩子
    @app.before_first_request
    def init_cloud():
        try:
            init_cloud_storage()
        except Exception as e:
            logger.warning(f"云存储初始化失败: {e}")

    # 定时任务（如果使用APScheduler）
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=schedule_auto_backup,
            trigger='interval',
            hours=24,  # 每24小时备份一次
            id='auto_backup'
        )
        scheduler.add_job(
            func=health_check,
            trigger='interval',
            hours=6,   # 每6小时健康检查一次
            id='health_check'
        )
        scheduler.start()

        logger.info("云存储定时任务已启动")

    except ImportError:
        logger.warning("APScheduler未安装，自动备份功能不可用")
    except Exception as e:
        logger.error(f"启动云存储定时任务失败: {e}")


# 导入便利函数
def enable_cloud_storage(app, config_path='cloud_config.json'):
    """启用云存储功能"""
    try:
        # 初始化云存储
        init_cloud_storage(config_path)

        # 注册路由
        register_cloud_routes(app)

        logger.info("云存储功能已启用")
        return True

    except Exception as e:
        logger.error(f"启用云存储功能失败: {e}")
        return False