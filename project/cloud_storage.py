"""
云存储模块 - 支持多种云存储服务
提供免费云存储功能：AWS S3、Google Cloud Storage、Azure Blob Storage
"""

import os
import json
import base64
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from google.cloud import storage as gcs
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List

class CloudStorageManager:
    """云存储管理器 - 统一接口支持多个云服务"""

    def __init__(self, provider='aws_s3', config: Dict = None):
        """
        初始化云存储管理器

        Args:
            provider: 云服务提供商 ('aws_s3', 'gcs', 'azure_b2', 'firebase')
            config: 配置字典
        """
        self.provider = provider
        self.config = config or {}
        self.client = None
        self.bucket_name = self.config.get('bucket_name', 'face-attendance-backup')

        # 设置日志
        self.logger = logging.getLogger(__name__)

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化云存储客户端"""
        try:
            if self.provider == 'aws_s3':
                self._init_aws_s3()
            elif self.provider == 'gcs':
                self._init_google_cloud_storage()
            elif self.provider == 'azure_b2':
                self._init_azure_blob()
            elif self.provider == 'firebase':
                self._init_firebase_storage()
            else:
                raise ValueError(f"不支持的云服务提供商: {self.provider}")

            self.logger.info(f"成功初始化 {self.provider} 云存储客户端")

        except Exception as e:
            self.logger.error(f"初始化云存储客户端失败: {e}")
            raise

    def _init_aws_s3(self):
        """初始化AWS S3客户端"""
        try:
            # 尝试从环境变量获取凭证
            access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

            if access_key and secret_key:
                # 使用显式凭证
                self.client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                # 使用IAM角色或默认凭证链
                self.client = boto3.client('s3', region_name=region)

            # 测试连接
            self.client.head_bucket(Bucket=self.bucket_name)

        except NoCredentialsError:
            raise Exception("AWS凭证未配置，请设置环境变量 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # 存储桶不存在，尝试创建
                self._create_s3_bucket()
            else:
                raise

    def _init_google_cloud_storage(self):
        """初始化Google Cloud Storage客户端"""
        try:
            # 从环境变量获取凭证路径
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

            if credentials_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

            self.client = gcs.Client()

            # 测试连接和存储桶
            bucket = self.client.bucket(self.bucket_name)
            bucket.reload()

        except Exception as e:
            raise Exception(f"Google Cloud Storage初始化失败: {e}")

    def _init_azure_blob(self):
        """初始化Azure Blob Storage客户端"""
        try:
            # 从环境变量获取连接字符串
            connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')

            if not connection_string:
                raise Exception("Azure连接字符串未配置，请设置环境变量 AZURE_STORAGE_CONNECTION_STRING")

            self.client = BlobServiceClient.from_connection_string(connection_string)

            # 测试连接和容器
            container_client = self.client.get_container_client(self.bucket_name)
            container_client.get_container_properties()

        except Exception as e:
            raise Exception(f"Azure Blob Storage初始化失败: {e}")

    def _init_firebase_storage(self):
        """初始化Firebase Storage客户端"""
        try:
            from firebase_admin import credentials, storage

            # 从环境变量获取Firebase配置
            firebase_config = os.environ.get('FIREBASE_CONFIG')

            if firebase_config:
                config_dict = json.loads(firebase_config)
                cred = credentials.Certificate(config_dict)
                firebase_app = storage.initialize_app(cred, {'storageBucket': self.bucket_name})
                self.client = storage.bucket()
            else:
                raise Exception("Firebase配置未设置，请设置环境变量 FIREBASE_CONFIG")

        except Exception as e:
            raise Exception(f"Firebase Storage初始化失败: {e}")

    def _create_s3_bucket(self):
        """创建S3存储桶"""
        try:
            self.client.create_bucket(Bucket=self.bucket_name)
            self.logger.info(f"成功创建S3存储桶: {self.bucket_name}")
        except ClientError as e:
            self.logger.error(f"创建S3存储桶失败: {e}")
            raise

    def upload_file(self, local_path: str, remote_path: str, metadata: Dict = None) -> bool:
        """
        上传文件到云存储

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            metadata: 文件元数据

        Returns:
            bool: 上传是否成功
        """
        try:
            if self.provider == 'aws_s3':
                return self._upload_to_s3(local_path, remote_path, metadata)
            elif self.provider == 'gcs':
                return self._upload_to_gcs(local_path, remote_path, metadata)
            elif self.provider == 'azure_b2':
                return self._upload_to_azure(local_path, remote_path, metadata)
            elif self.provider == 'firebase':
                return self._upload_to_firebase(local_path, remote_path, metadata)

        except Exception as e:
            self.logger.error(f"文件上传失败: {e}")
            return False

    def _upload_to_s3(self, local_path: str, remote_path: str, metadata: Dict = None) -> bool:
        """上传文件到AWS S3"""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            self.client.upload_file(local_path, self.bucket_name, remote_path, ExtraArgs=extra_args)
            return True
        except Exception as e:
            self.logger.error(f"S3上传失败: {e}")
            return False

    def _upload_to_gcs(self, local_path: str, remote_path: str, metadata: Dict = None) -> bool:
        """上传文件到Google Cloud Storage"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_filename(local_path)
            return True
        except Exception as e:
            self.logger.error(f"GCS上传失败: {e}")
            return False

    def _upload_to_azure(self, local_path: str, remote_path: str, metadata: Dict = None) -> bool:
        """上传文件到Azure Blob Storage"""
        try:
            blob_client = self.client.get_blob_client(container=self.bucket_name, blob=remote_path)

            with open(local_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True, metadata=metadata)

            return True
        except Exception as e:
            self.logger.error(f"Azure上传失败: {e}")
            return False

    def _upload_to_firebase(self, local_path: str, remote_path: str, metadata: Dict = None) -> bool:
        """上传文件到Firebase Storage"""
        try:
            blob = self.client.blob(remote_path)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_filename(local_path)
            return True
        except Exception as e:
            self.logger.error(f"Firebase上传失败: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        从云存储下载文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径

        Returns:
            bool: 下载是否成功
        """
        try:
            if self.provider == 'aws_s3':
                return self._download_from_s3(remote_path, local_path)
            elif self.provider == 'gcs':
                return self._download_from_gcs(remote_path, local_path)
            elif self.provider == 'azure_b2':
                return self._download_from_azure(remote_path, local_path)
            elif self.provider == 'firebase':
                return self._download_from_firebase(remote_path, local_path)

        except Exception as e:
            self.logger.error(f"文件下载失败: {e}")
            return False

    def _download_from_s3(self, remote_path: str, local_path: str) -> bool:
        """从AWS S3下载文件"""
        try:
            self.client.download_file(self.bucket_name, remote_path, local_path)
            return True
        except Exception as e:
            self.logger.error(f"S3下载失败: {e}")
            return False

    def _download_from_gcs(self, remote_path: str, local_path: str) -> bool:
        """从Google Cloud Storage下载文件"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)
            blob.download_to_filename(local_path)
            return True
        except Exception as e:
            self.logger.error(f"GCS下载失败: {e}")
            return False

    def _download_from_azure(self, remote_path: str, local_path: str) -> bool:
        """从Azure Blob Storage下载文件"""
        try:
            blob_client = self.client.get_blob_client(container=self.bucket_name, blob=remote_path)
            with open(local_path, 'wb') as data:
                data.write(blob_client.download_blob().readall())
            return True
        except Exception as e:
            self.logger.error(f"Azure下载失败: {e}")
            return False

    def _download_from_firebase(self, remote_path: str, local_path: str) -> bool:
        """从Firebase Storage下载文件"""
        try:
            blob = self.client.blob(remote_path)
            blob.download_to_filename(local_path)
            return True
        except Exception as e:
            self.logger.error(f"Firebase下载失败: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """
        删除云存储中的文件

        Args:
            remote_path: 远程文件路径

        Returns:
            bool: 删除是否成功
        """
        try:
            if self.provider == 'aws_s3':
                return self._delete_from_s3(remote_path)
            elif self.provider == 'gcs':
                return self._delete_from_gcs(remote_path)
            elif self.provider == 'azure_b2':
                return self._delete_from_azure(remote_path)
            elif self.provider == 'firebase':
                return self._delete_from_firebase(remote_path)

        except Exception as e:
            self.logger.error(f"文件删除失败: {e}")
            return False

    def _delete_from_s3(self, remote_path: str) -> bool:
        """从AWS S3删除文件"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=remote_path)
            return True
        except Exception as e:
            self.logger.error(f"S3删除失败: {e}")
            return False

    def _delete_from_gcs(self, remote_path: str) -> bool:
        """从Google Cloud Storage删除文件"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception as e:
            self.logger.error(f"GCS删除失败: {e}")
            return False

    def _delete_from_azure(self, remote_path: str) -> bool:
        """从Azure Blob Storage删除文件"""
        try:
            blob_client = self.client.get_blob_client(container=self.bucket_name, blob=remote_path)
            blob_client.delete_blob()
            return True
        except Exception as e:
            self.logger.error(f"Azure删除失败: {e}")
            return False

    def _delete_from_firebase(self, remote_path: str) -> bool:
        """从Firebase Storage删除文件"""
        try:
            blob = self.client.blob(remote_path)
            blob.delete()
            return True
        except Exception as e:
            self.logger.error(f"Firebase删除失败: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        """
        列出云存储中的文件

        Args:
            prefix: 文件名前缀

        Returns:
            List[str]: 文件列表
        """
        try:
            if self.provider == 'aws_s3':
                return self._list_s3_files(prefix)
            elif self.provider == 'gcs':
                return self._list_gcs_files(prefix)
            elif self.provider == 'azure_b2':
                return self._list_azure_files(prefix)
            elif self.provider == 'firebase':
                return self._list_firebase_files(prefix)

        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
            return []

    def _list_s3_files(self, prefix: str) -> List[str]:
        """列出AWS S3中的文件"""
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            self.logger.error(f"S3列出文件失败: {e}")
            return []

    def _list_gcs_files(self, prefix: str) -> List[str]:
        """列出Google Cloud Storage中的文件"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            self.logger.error(f"GCS列出文件失败: {e}")
            return []

    def _list_azure_files(self, prefix: str) -> List[str]:
        """列出Azure Blob Storage中的文件"""
        try:
            container_client = self.client.get_container_client(self.bucket_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            self.logger.error(f"Azure列出文件失败: {e}")
            return []

    def _list_firebase_files(self, prefix: str) -> List[str]:
        """列出Firebase Storage中的文件"""
        try:
            blobs = self.client.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            self.logger.error(f"Firebase列出文件失败: {e}")
            return []

    def get_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息

        Args:
            remote_path: 远程文件路径

        Returns:
            Optional[Dict]: 文件信息
        """
        try:
            if self.provider == 'aws_s3':
                return self._get_s3_file_info(remote_path)
            elif self.provider == 'gcs':
                return self._get_gcs_file_info(remote_path)
            elif self.provider == 'azure_b2':
                return self._get_azure_file_info(remote_path)
            elif self.provider == 'firebase':
                return self._get_firebase_file_info(remote_path)

        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return None

    def _get_s3_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取AWS S3文件信息"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=remote_path)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {})
            }
        except Exception as e:
            self.logger.error(f"S3获取文件信息失败: {e}")
            return None

    def _get_gcs_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取Google Cloud Storage文件信息"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)
            blob.reload()

            if blob.exists():
                return {
                    'size': blob.size,
                    'last_modified': blob.time_created,
                    'metadata': blob.metadata or {}
                }
            return None
        except Exception as e:
            self.logger.error(f"GCS获取文件信息失败: {e}")
            return None

    def _get_azure_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取Azure Blob Storage文件信息"""
        try:
            blob_client = self.client.get_blob_client(container=self.bucket_name, blob=remote_path)
            blob = blob_client.get_blob_properties()

            return {
                'size': blob.size,
                'last_modified': blob.last_modified,
                'metadata': blob.metadata or {}
            }
        except Exception as e:
            self.logger.error(f"Azure获取文件信息失败: {e}")
            return None

    def _get_firebase_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取Firebase Storage文件信息"""
        try:
            blob = self.client.blob(remote_path)
            blob.reload()

            if blob.exists():
                return {
                    'size': blob.size,
                    'last_modified': blob.time_created,
                    'metadata': blob.metadata or {}
                }
            return None
        except Exception as e:
            self.logger.error(f"Firebase获取文件信息失败: {e}")
            return None


class CloudBackupManager:
    """云备份管理器 - 专门处理数据库和重要文件的备份"""

    def __init__(self, storage_provider='aws_s3', config: Dict = None):
        """
        初始化云备份管理器

        Args:
            storage_provider: 云服务提供商
            config: 配置字典
        """
        self.storage = CloudStorageManager(storage_provider, config)
        self.logger = logging.getLogger(__name__)

        # 备份配置
        self.backup_config = config or {}
        self.auto_backup = self.backup_config.get('auto_backup', True)
        self.backup_frequency = self.backup_config.get('backup_frequency', 24)  # 小时
        self.max_backups = self.backup_config.get('max_backups', 30)
        self.backup_prefix = self.backup_config.get('backup_prefix', 'backup/')

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
            success = self.storage.upload_file(db_path, remote_path, {
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
                success = self.storage.upload_file(temp_file.name, remote_path, {
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

    def restore_database(self, backup_path: str, local_path: str) -> bool:
        """
        从云存储恢复数据库

        Args:
            backup_path: 云存储备份路径
            local_path: 本地恢复路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            # 下载备份文件
            success = self.storage.download_file(backup_path, local_path)

            if success:
                self.logger.info(f"数据库恢复成功: {backup_path}")
                return True
            else:
                self.logger.error("数据库恢复失败")
                return False

        except Exception as e:
            self.logger.error(f"数据库恢复异常: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份

        Returns:
            List[Dict]: 备份列表
        """
        try:
            files = self.storage.list_files(self.backup_prefix)
            backups = []

            for file in files:
                if file.startswith(self.backup_prefix):
                    file_info = self.storage.get_file_info(file)
                    if file_info:
                        backup_info = {
                            'name': file,
                            'size': file_info['size'],
                            'last_modified': file_info['last_modified'],
                            'type': self._get_backup_type(file)
                        }
                        backups.append(backup_info)

            # 按修改时间排序
            backups.sort(key=lambda x: x['last_modified'], reverse=True)
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
                    self.storage.delete_file(backup['name'])
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


def get_cloud_storage_config(provider: str = 'aws_s3') -> Dict:
    """
    获取云存储配置模板

    Args:
        provider: 云服务提供商

    Returns:
        Dict: 配置模板
    """
    configs = {
        'aws_s3': {
            'provider': 'aws_s3',
            'bucket_name': 'face-attendance-backup',
            'config': {
                'region': 'us-east-1',
                'access_key_id': os.environ.get('AWS_ACCESS_KEY_ID', ''),
                'secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
                'session_token': os.environ.get('AWS_SESSION_TOKEN', '')
            }
        },
        'gcs': {
            'provider': 'gcs',
            'bucket_name': 'face-attendance-backup',
            'config': {
                'credentials_path': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
                'project_id': os.environ.get('GOOGLE_PROJECT_ID', '')
            }
        },
        'azure_b2': {
            'provider': 'azure_b2',
            'bucket_name': 'face-attendance-backup',
            'config': {
                'connection_string': os.environ.get('AZURE_STORAGE_CONNECTION_STRING', ''),
                'account_name': os.environ.get('AZURE_STORAGE_ACCOUNT_NAME', ''),
                'account_key': os.environ.get('AZURE_STORAGE_ACCOUNT_KEY', '')
            }
        },
        'firebase': {
            'provider': 'firebase',
            'bucket_name': 'face-attendance-backup',
            'config': {
                'firebase_config': os.environ.get('FIREBASE_CONFIG', '')
            }
        }
    }

    return configs.get(provider, configs['aws_s3'])


def setup_cloud_storage(provider: str = 'aws_s3', config: Dict = None) -> CloudStorageManager:
    """
    设置云存储管理器

    Args:
        provider: 云服务提供商
        config: 自定义配置

    Returns:
        CloudStorageManager: 云存储管理器实例
    """
    try:
        if config is None:
            config = get_cloud_storage_config(provider)

        storage_manager = CloudStorageManager(provider, config)
        return storage_manager

    except Exception as e:
        logging.error(f"设置云存储失败: {e}")
        raise