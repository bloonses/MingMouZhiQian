"""
Backblaze B2 永久免费云存储专用模块
专为需要10GB永久免费存储的用户优化
"""

import os
import base64
import hashlib
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

class BackblazeB2Manager:
    """Backblaze B2 云存储管理器"""

    def __init__(self, config: Dict = None):
        """
        初始化B2管理器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.application_key_id = self.config.get('application_key_id', '')
        self.application_key = self.config.get('application_key', '')
        self.bucket_name = self.config.get('bucket_name', 'face-attendance-backup')
        self.bucket_id = self.config.get('bucket_id', '')
        self.download_url = self.config.get('download_url', 'https://f004.backblazeb2.com/file')

        # API端点
        self.api_url = 'https://api001.backblazeb2.com'
        self.download_url_base = 'https://f002.backblazeb2.com/file'

        # 会话信息
        self.auth_token = None
        self.api_url_base = None
        self.account_id = None

        # 设置日志
        self.logger = logging.getLogger(__name__)

        # 初始化连接
        self._authorize()

    def _authorize(self):
        """授权B2 API"""
        try:
            auth_url = f"{self.api_url}/b2api/v2/b2_authorize_account"

            # Base64编码的凭证
            credentials = f"{self.application_key_id}:{self.application_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                'Authorization': f'Basic {encoded_credentials}'
            }

            response = requests.get(auth_url, headers=headers, timeout=30)
            response.raise_for_status()

            auth_data = response.json()
            self.auth_token = auth_data['authorizationToken']
            self.api_url_base = auth_data['apiUrl']
            self.account_id = auth_data['accountId']

            self.logger.info("Backblaze B2 授权成功")

        except Exception as e:
            self.logger.error(f"B2授权失败: {e}")
            raise

    def _make_request(self, method: str, endpoint: str, data: Dict = None,
                      bucket_name: str = None, download: bool = False) -> Dict:
        """发送B2 API请求"""
        try:
            url = f"{self.api_url_base}{endpoint}"

            headers = {
                'Authorization': self.auth_token
            }

            # 如果是下载请求，使用下载URL
            if download and bucket_name:
                url = f"{self.download_url_base}/{bucket_name}/{endpoint.strip('/')}"
                headers.pop('Authorization', None)  # 下载请求不需要授权令牌

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.logger.error(f"B2 API请求失败 [{method} {endpoint}]: {e}")
            raise

    def get_bucket_info(self) -> Dict:
        """获取存储桶信息"""
        try:
            # 列出存储桶
            buckets = self._make_request('POST', '/b2api/v2/b2_list_buckets', {
                'accountId': self.account_id
            })

            # 找到目标存储桶
            for bucket in buckets['buckets']:
                if bucket['bucketName'] == self.bucket_name:
                    return bucket

            # 如果不存在，创建存储桶
            return self._create_bucket()

        except Exception as e:
            self.logger.error(f"获取存储桶信息失败: {e}")
            raise

    def _create_bucket(self) -> Dict:
        """创建存储桶"""
        try:
            bucket_data = self._make_request('POST', '/b2api/v2/b2_create_bucket', {
                'accountId': self.account_id,
                'bucketName': self.bucket_name,
                'bucketType': 'allPrivate'  # 私有存储桶
            })

            self.logger.info(f"存储桶 {self.bucket_name} 创建成功")
            return bucket_data

        except Exception as e:
            self.logger.error(f"创建存储桶失败: {e}")
            raise

    def upload_file(self, local_path: str, remote_path: str,
                   content_type: str = 'application/octet-stream',
                   metadata: Dict = None) -> bool:
        """
        上传文件到B2

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            content_type: 文件内容类型
            metadata: 文件元数据

        Returns:
            bool: 上传是否成功
        """
        try:
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"本地文件不存在: {local_path}")

            # 获取上传URL
            upload_info = self._make_request('POST', '/b2api/v2/b2_get_upload_url', {
                'bucketId': self.bucket_id
            })

            # 读取文件内容
            with open(local_path, 'rb') as f:
                file_content = f.read()

            # 计算文件_sha1
            file_sha1 = hashlib.sha1(file_content).hexdigest()

            # 构建上传头
            headers = {
                'Authorization': upload_info['authorizationToken'],
                'X-Bz-File-Name': remote_path,
                'Content-Type': content_type,
                'X-Bz-Content-Sha1': file_sha1
            }

            # 添加元数据
            if metadata:
                for key, value in metadata.items():
                    headers[f'X-Bz-Info-{key}'] = str(value)

            # 上传文件
            upload_url = upload_info['uploadUrl']
            response = requests.post(upload_url, headers=headers, data=file_content, timeout=60)

            response.raise_for_status()
            upload_result = response.json()

            self.logger.info(f"文件上传成功: {remote_path} ({len(file_content)} bytes)")
            return True

        except Exception as e:
            self.logger.error(f"文件上传失败: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        从B2下载文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径

        Returns:
            bool: 下载是否成功
        """
        try:
            # 构建下载URL
            download_url = f"{self.download_url_base}/{self.bucket_name}/{remote_path}"

            # 发送下载请求
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()

            # 确保目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 保存文件
            with open(local_path, 'wb') as f:
                f.write(response.content())

            self.logger.info(f"文件下载成功: {remote_path} -> {local_path} ({len(response.content)} bytes)")
            return True

        except Exception as e:
            self.logger.error(f"文件下载失败: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """
        从B2删除文件

        Args:
            remote_path: 远程文件路径

        Returns:
            bool: 删除是否成功
        """
        try:
            # 获取文件信息
            file_list = self._make_request('POST', '/b2api/v2/b2_list_file_names', {
                'bucketId': self.bucket_id,
                'prefix': remote_path,
                'maxFileCount': 1
            })

            if not file_list.get('files'):
                self.logger.warning(f"文件不存在: {remote_path}")
                return False

            file_info = file_list['files'][0]
            file_id = file_info['fileId']

            # 删除文件
            delete_result = self._make_request('POST', '/b2api/v2/b2_delete_file_version', {
                'fileId': file_id,
                'fileName': remote_path
            })

            self.logger.info(f"文件删除成功: {remote_path}")
            return True

        except Exception as e:
            self.logger.error(f"文件删除失败: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        """
        列出B2中的文件

        Args:
            prefix: 文件名前缀

        Returns:
            List[str]: 文件列表
        """
        try:
            files = []
            continuation_token = None

            while True:
                # 构建请求参数
                params = {
                    'bucketId': self.bucket_id,
                    'prefix': prefix,
                    'maxFileCount': 1000
                }

                if continuation_token:
                    params['continuationToken'] = continuation_token

                # 获取文件列表
                file_list = self._make_request('POST', '/b2api/v2/b2_list_file_names', params)

                # 添加文件到结果列表
                for file_info in file_list.get('files', []):
                    files.append(file_info['fileName'])

                # 检查是否有更多文件
                if file_list.get('nextFileName'):
                    # 使用文件名作为continuation token
                    continuation_token = file_list['files'][-1]['fileName']
                else:
                    break

            return files

        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
            return []

    def get_file_info(self, remote_path: str) -> Optional[Dict]:
        """
        获取文件信息

        Args:
            remote_path: 远程文件路径

        Returns:
            Optional[Dict]: 文件信息
        """
        try:
            file_list = self._make_request('POST', '/b2api/v2/b2_list_file_names', {
                'bucketId': self.bucket_id,
                'prefix': remote_path,
                'maxFileCount': 1
            })

            if file_list.get('files'):
                file_info = file_list['files'][0]
                return {
                    'name': file_info['fileName'],
                    'size': file_info['size'],
                    'upload_timestamp': file_info['uploadTimestamp'],
                    'content_type': file_info.get('contentType', 'application/octet-stream'),
                    'content_sha1': file_info.get('contentSha1', ''),
                    'file_id': file_info['fileId']
                }

            return None

        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return None


class BackblazeBackupManager:
    """Backblaze B2 备份管理器"""

    def __init__(self, config: Dict = None):
        """
        初始化备份管理器

        Args:
            config: 配置字典
        """
        self.b2_manager = BackblazeB2Manager(config)
        self.config = config or {}
        self.backup_prefix = self.config.get('backup_prefix', 'backup/')
        self.max_backups = self.config.get('max_backups', 30)

        # 设置日志
        self.logger = logging.getLogger(__name__)

    def backup_database(self, db_path: str) -> bool:
        """
        备份数据库文件

        Args:
            db_path: 数据库文件路径

        Returns:
            bool: 备份是否成功
        """
        try:
            if not os.path.exists(db_path):
                self.logger.error(f"数据库文件不存在: {db_path}")
                return False

            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'database_backup_{timestamp}.db'
            remote_path = f"{self.backup_prefix}{backup_name}"

            # 上传备份
            success = self.b2_manager.upload_file(db_path, remote_path, {
                'content_type': 'application/x-sqlite3',
                'backup_type': 'database',
                'timestamp': timestamp,
                'original_name': os.path.basename(db_path)
            })

            if success:
                self.logger.info(f"数据库备份成功: {backup_name}")

                # 清理旧备份
                self._cleanup_old_backups()
                return True
            else:
                self.logger.error("数据库备份失败")
                return False

        except Exception as e:
            self.logger.error(f"数据库备份异常: {e}")
            return False

    def backup_student_faces(self, faces_dir: str) -> bool:
        """
        备份学生人脸数据

        Args:
            faces_dir: 人脸数据目录

        Returns:
            bool: 备份是否成功
        """
        try:
            if not os.path.exists(faces_dir):
                self.logger.error(f"人脸数据目录不存在: {faces_dir}")
                return False

            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'student_faces_backup_{timestamp}.tar.gz'
            remote_path = f"{self.backup_prefix}{backup_name}"

            # 打包人脸数据
            import tarfile
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
                with tarfile.open(temp_file.name, 'w:gz') as tar:
                    for root, dirs, files in os.walk(faces_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, faces_dir)
                            tar.add(file_path, arcname=arcname)

                # 上传备份
                success = self.b2_manager.upload_file(temp_file.name, remote_path, {
                    'content_type': 'application/gzip',
                    'backup_type': 'student_faces',
                    'timestamp': timestamp,
                    'faces_dir': faces_dir
                })

                # 清理临时文件
                os.unlink(temp_file.name)

            if success:
                self.logger.info(f"人脸数据备份成功: {backup_name}")

                # 清理旧备份
                self._cleanup_old_backups()
                return True
            else:
                self.logger.error("人脸数据备份失败")
                return False

        except Exception as e:
            self.logger.error(f"人脸数据备份异常: {e}")
            return False

    def restore_database(self, backup_name: str, local_path: str) -> bool:
        """
        从B2恢复数据库

        Args:
            backup_name: 备份文件名
            local_path: 本地恢复路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            remote_path = f"{self.backup_prefix}{backup_name}"

            # 下载备份
            success = self.b2_manager.download_file(remote_path, local_path)

            if success:
                self.logger.info(f"数据库恢复成功: {backup_name}")
                return True
            else:
                self.logger.error("数据库恢复失败")
                return False

        except Exception as e:
            self.logger.error(f"数据库恢复异常: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """
        列出所有备份

        Returns:
            List[Dict]: 备份列表
        """
        try:
            files = self.b2_manager.list_files(self.backup_prefix)
            backups = []

            for file in files:
                if file.startswith(self.backup_prefix):
                    file_info = self.b2_manager.get_file_info(file)
                    if file_info:
                        backup_info = {
                            'name': file,
                            'size': file_info['size'],
                            'upload_timestamp': file_info['upload_timestamp'],
                            'type': self._get_backup_type(file),
                            'file_id': file_info['file_id']
                        }
                        backups.append(backup_info)

            # 按上传时间排序
            backups.sort(key=lambda x: x['upload_timestamp'], reverse=True)
            return backups

        except Exception as e:
            self.logger.error(f"列出备份失败: {e}")
            return []

    def _cleanup_old_backups(self):
        """清理旧备份，保留最近的N个备份"""
        try:
            backups = self.list_backups()

            # 删除超过最大备份数量的旧备份
            if len(backups) > self.max_backups:
                for backup in backups[self.max_backups:]:
                    self.b2_manager.delete_file(backup['name'])
                    self.logger.info(f"删除旧备份: {backup['name']}")

        except Exception as e:
            self.logger.error(f"清理旧备份失败: {e}")

    def _get_backup_type(self, filename: str) -> str:
        """根据文件名判断备份类型"""
        if 'database' in filename:
            return 'database'
        elif 'student_faces' in filename:
            return 'student_faces'
        else:
            return 'unknown'

    def get_backup_status(self) -> Dict:
        """获取备份状态"""
        try:
            backups = self.list_backups()
            total_size = sum(backup['size'] for backup in backups)

            return {
                'total_backups': len(backups),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_backup': backups[-1]['upload_timestamp'] if backups else None,
                'newest_backup': backups[0]['upload_timestamp'] if backups else None,
                'backup_types': len(set(backup['type'] for backup in backups))
            }
        except Exception as e:
            self.logger.error(f"获取备份状态失败: {e}")
            return {
                'total_backups': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'backup_types': 0
            }


def create_backblaze_config() -> Dict:
    """创建Backblaze B2配置"""
    config = {
        'provider': 'backblaze_b2',
        'bucket_name': 'face-attendance-backup',
        'config': {
            'application_key_id': os.environ.get('B2_APPLICATION_KEY_ID', ''),
            'application_key': os.environ.get('B2_APPLICATION_KEY', ''),
            'bucket_name': os.environ.get('B2_BUCKET_NAME', 'face-attendance-backup'),
            'bucket_id': os.environ.get('B2_BUCKET_ID', ''),
            'download_url': 'https://f004.backblazeb2.com/file'
        },
        'backup_prefix': 'backup/',
        'max_backups': 30
    }

    # 保存配置文件
    with open('backblaze_b2_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("✅ Backblaze B2配置文件已创建: backblaze_b2_config.json")
    return config


def setup_backblaze_guide():
    """设置Backblaze B2指南"""
    print("=" * 80)
    print("🎯 Backblaze B2 永久免费设置指南")
    print("=" * 80)

    print("\n📊 Backblaze B2 免费层优势:")
    print("   ✅ 10GB 永久免费存储空间")
    print("   ✅ 1GB/天 免费下载流量")
    print("   ✅ 无限制 上传")
    print("   ✅ 永久免费（无时间限制）")
    print("   ✅ 足够存储5年的人脸考勤数据")

    print("\n🚀 设置步骤:")

    steps = [
        "1. 访问 Backblaze 官网注册",
        "2. 进入 B2 云存储服务",
        "3. 创建存储桶",
        "4. 生成应用密钥",
        "5. 配置环境变量",
        "6. 测试连接",
        "7. 启用自动备份"
    ]

    for i, step in enumerate(steps, 1):
        print(f"   {i}. {step}")

    print("\n📝 详细设置说明:")
    print("1. 注册账号: https://www.backblaze.com/b2/")
    print("2. 登录后进入 'B2 Cloud Storage'")
    print("3. 点击 'Create a Bucket'")
    print("4. Bucket Name: face-attendance-backup")
    print("5. Bucket Type: Private")
    print("6. 创建后记下 Bucket ID")
    print("7. 进入 'App Keys' 创建新密钥")
    print("8. 保存 KeyID 和 Application Key")

    print("\n⚠️ 重要提示:")
    print("   • KeyID 和 Application Key 要妥善保管")
    print("   • 每次只能看到一个密钥，请务必保存")
    print("   • 存储桶名称必须全局唯一")

    # 创建配置文件
    print("\n📁 创建配置文件...")
    config = create_backblaze_config()

    # 创建环境变量模板
    env_template = f'''# Backblaze B2 永久免费环境变量配置
# 复制此文件为 .env 并填入您的实际配置

# Backblaze B2 配置（10GB永久免费）
B2_APPLICATION_KEY_ID={config['config']['application_key_id']}
B2_APPLICATION_KEY={config['config']['application_key']}
B2_BUCKET_NAME={config['config']['bucket_name']}
B2_BUCKET_ID={config['config']['bucket_id']}
B2_DOWNLOAD_URL={config['config']['download_url']}
'''

    with open('.env_backblaze', 'w', encoding='utf-8') as f:
        f.write(env_template)

    print("✅ 环境变量模板已创建: .env_backblaze")

    print("\n🎉 Backblaze B2 配置完成！")
    print("\n💡 下一步:")
    print("1. 访问 https://www.backblaze.com/b2/ 注册账号")
    print("2. 创建存储桶并获取访问凭证")
    print("3. 修改 .env_backblaze 文件填入实际凭证")
    print("4. 运行 python demo_cloud_storage.py 测试功能")

    print("\n📊 存储容量规划:")
    print("   • 当前数据: ~215MB")
    print("   • 1年数据: ~2.58GB")
    print("   • 5年数据: ~12.9GB")
    print("   • 免费限额: 10GB")
    print("   • 剩余空间: 5年内约-2.9GB (可能需要清理)")

if __name__ == "__main__":
    setup_backblaze_guide()