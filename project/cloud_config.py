"""
免费云存储配置指南
支持：AWS S3、Google Cloud Storage、Azure Blob Storage
"""

import os
import json
from typing import Dict, Any

class CloudStorageConfig:
    """云存储配置管理器"""

    @staticmethod
    def get_aws_s3_config() -> Dict[str, Any]:
        """获取AWS S3免费配置"""
        return {
            'provider': 'aws_s3',
            'bucket_name': 'face-attendance-backup-unique-name',  # 必须唯一
            'config': {
                # AWS免费层配置
                # 1. 注册AWS账号：https://aws.amazon.com/free/
                # 2. 进入S3控制台：https://s3.console.aws.amazon.com/
                # 3. 创建存储桶，名称必须全局唯一
                'region': 'us-east-1',
                'access_key_id': os.environ.get('AWS_ACCESS_KEY_ID', ''),
                'secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY', '')
            }
        }

    @staticmethod
    def get_gcs_config() -> Dict[str, Any]:
        """获取Google Cloud Storage免费配置"""
        return {
            'provider': 'gcs',
            'bucket_name': 'face-attendance-backup-unique-name',  # 必须唯一
            'config': {
                # GCS免费层配置
                # 1. 注册Google Cloud账号：https://cloud.google.com/free
                # 2. 启用Cloud Storage API
                # 3. 创建存储桶，名称必须全局唯一
                'credentials_path': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
                'project_id': os.environ.get('GOOGLE_PROJECT_ID', '')
            }
        }

    @staticmethod
    def get_azure_config() -> Dict[str, Any]:
        """获取Azure Blob Storage免费配置"""
        return {
            'provider': 'azure_b2',
            'bucket_name': 'faceattendancebackup',  # Azure容器名
            'config': {
                # Azure免费层配置
                # 1. 注册Azure账号：https://azure.microsoft.com/free
                # 2. 创建存储账户
                # 3. 获取连接字符串
                'connection_string': os.environ.get('AZURE_STORAGE_CONNECTION_STRING', ''),
                'account_name': os.environ.get('AZURE_STORAGE_ACCOUNT_NAME', ''),
                'account_key': os.environ.get('AZURE_STORAGE_ACCOUNT_KEY', '')
            }
        }

    @staticmethod
    def get_config(provider: str = 'aws_s3') -> Dict[str, Any]:
        """获取指定配置提供商的配置"""
        configs = {
            'aws_s3': CloudStorageConfig.get_aws_s3_config(),
            'gcs': CloudStorageConfig.get_gcs_config(),
            'azure': CloudStorageConfig.get_azure_config()
        }
        return configs.get(provider, configs['aws_s3'])

    @staticmethod
    def create_config_file(provider: str = 'aws_s3', filename: str = 'cloud_config.json'):
        """创建配置文件"""
        config = CloudStorageConfig.get_config(provider)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"配置文件已创建: {filename}")
        return config

    @staticmethod
    def load_config(filename: str = 'cloud_config.json') -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件不存在: {filename}")
            return None
        except json.JSONDecodeError:
            print(f"配置文件格式错误: {filename}")
            return None


class FreeTierInfo:
    """免费层信息"""

    @staticmethod
    def get_aws_s3_free_tier() -> Dict[str, str]:
        """AWS S3免费层信息"""
        return {
            'name': 'AWS S3 免费层',
            'storage': '5GB 存储空间',
            'requests': '每月 20,000 GET 请求 + 2,000 PUT 请求',
            'duration': '12个月免费',
            'features': [
                '5GB S3标准存储',
                '20,000 GET请求',
                '2,000 PUT请求',
                '数据传输（免费流入）'
            ],
            'setup_link': 'https://aws.amazon.com/s3/pricing/',
            'guide_link': 'https://aws.amazon.com/getting-started/'
        }

    @staticmethod
    def get_gcs_free_tier() -> Dict[str, str]:
        """Google Cloud Storage免费层信息"""
        return {
            'name': 'Google Cloud Storage 免费层',
            'storage': '5GB 存储空间',
            'requests': '每月 50,000 次读取 + 20,000 次写入',
            'duration': '永久免费（有使用限制）',
            'features': [
                '5GB 标准存储',
                '50,000次读取操作',
                '20,000次写入操作',
                '每月1GB数据流出'
            ],
            'setup_link': 'https://cloud.google.com/storage/free',
            'guide_link': 'https://cloud.google.com/docs/getting-started'
        }

    @staticmethod
    def get_azure_free_tier() -> Dict[str, str]:
        """Azure Blob Storage免费层信息"""
        return {
            'name': 'Azure Blob Storage 免费层',
            'storage': '5GB 存储空间',
            'requests': '每月 50,000 次读取 + 20,000 次写入',
            'duration': '永久免费（有使用限制）',
            'features': [
                '5GB 热层存储',
                '50,000次读取请求',
                '20,000次写入请求',
                '每月1GB数据传输'
            ],
            'setup_link': 'https://azure.microsoft.com/en-us/free/',
            'guide_link': 'https://learn.microsoft.com/azure/storage/blobs/'
        }

    @staticmethod
    def display_provider_info(provider: str = 'aws_s3'):
        """显示提供商信息"""
        providers = {
            'aws_s3': FreeTierInfo.get_aws_s3_free_tier(),
            'gcs': FreeTierInfo.get_gcs_free_tier(),
            'azure': FreeTierInfo.get_azure_free_tier()
        }

        info = providers.get(provider)
        if not info:
            print("不支持的云服务提供商")
            return

        print(f"\n📦 {info['name']}")
        print(f"💾 存储空间: {info['storage']}")
        print(f"🔄 请求限制: {info['requests']}")
        print(f"⏰ 免费期限: {info['duration']}")
        print(f"🔧 功能特性:")
        for feature in info['features']:
            print(f"   • {feature}")
        print(f"🔗 设置链接: {info['setup_link']}")
        print(f"📖 指南链接: {info['guide_link']}")


def setup_guide():
    """设置指南"""
    print("=" * 60)
    print("🎯 免费云存储设置指南")
    print("=" * 60)

    # 显示所有提供商信息
    providers = ['aws_s3', 'gcs', 'azure']
    for provider in providers:
        FreeTierInfo.display_provider_info(provider)
        print("\n" + "-" * 60)

    print("🚀 快速设置步骤:")
    print("1. 选择一个云服务提供商")
    print("2. 注册账号并验证身份")
    print("3. 创建存储桶/容器")
    print("4. 获取访问凭证")
    print("5. 设置环境变量或创建配置文件")
    print("6. 运行云存储功能")

    print("\n📝 推荐选择:")
    print("• 初学者: AWS S3 (文档完善，易于使用)")
    print("• Google生态用户: Google Cloud Storage")
    print("• 企业用户: Azure Blob Storage")


if __name__ == "__main__":
    # 显示设置指南
    setup_guide()

    # 创建默认配置文件
    print("\n📁 创建默认配置文件...")
    config = CloudStorageConfig.create_config_file('aws_s3')
    print("配置文件已创建: cloud_config.json")
    print("请根据您的实际情况修改配置文件中的参数")