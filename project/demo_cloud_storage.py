"""
云存储功能演示脚本
展示如何使用云存储模块进行数据备份和恢复
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def print_section(title):
    """打印子标题"""
    print(f"\n📋 {title}")
    print("-" * 40)

def demo_cloud_storage():
    """演示云存储功能"""
    print_header("云存储功能演示")

    try:
        # 导入云存储模块
        from cloud_config import CloudStorageConfig, FreeTierInfo
        from cloud_storage import CloudStorageManager, CloudBackupManager

        print_section("1. 显示云服务提供商信息")
        FreeTierInfo.display_provider_info('aws_s3')

        print_section("2. 创建配置文件")
        config = CloudStorageConfig.create_config_file('aws_s3')
        print(f"✅ 配置文件已创建: cloud_config.json")

        print_section("3. 加载配置")
        loaded_config = CloudStorageConfig.load_config('cloud_config.json')
        if loaded_config:
            print(f"✅ 成功加载配置，提供商: {loaded_config['provider']}")
            print(f"✅ 存储桶名称: {loaded_config['bucket_name']}")
        else:
            print("❌ 配置加载失败")
            return

        print_section("4. 初始化云存储管理器")
        try:
            storage_manager = CloudStorageManager(loaded_config['provider'], loaded_config['config'])
            print(f"✅ 云存储管理器初始化成功")
        except Exception as e:
            print(f"⚠️  云存储连接需要配置凭证，这是正常的")
            print(f"   错误信息: {str(e)}")
            print(f"   请按照 README_CLOUD.md 配置您的云服务凭证")
            return

        print_section("5. 测试云存储操作")

        # 创建一个测试文件
        test_filename = "test_cloud_storage.txt"
        test_content = f"测试云存储功能\n时间: {datetime.now().isoformat()}\n这是一个测试文件，用于验证云存储功能。"

        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(test_content)

        print(f"✅ 创建测试文件: {test_filename}")

        # 上传文件
        remote_path = f"test/{test_filename}"
        print(f"📤 上传文件到: {remote_path}")

        try:
            upload_success = storage_manager.upload_file(test_filename, remote_path)
            if upload_success:
                print("✅ 文件上传成功")
            else:
                print("❌ 文件上传失败")
                return
        except Exception as e:
            print(f"⚠️  上传失败，请检查云存储配置: {str(e)}")
            return

        # 列出文件
        print("📋 云存储中的文件:")
        try:
            files = storage_manager.list_files()
            if files:
                for file in files[:5]:  # 只显示前5个文件
                    print(f"   • {file}")
                if len(files) > 5:
                    print(f"   ... 还有 {len(files)-5} 个文件")
            else:
                print("   没有找到文件")
        except Exception as e:
            print(f"❌ 列出文件失败: {str(e)}")
            return

        # 获取文件信息
        print(f"📊 文件信息:")
        try:
            file_info = storage_manager.get_file_info(remote_path)
            if file_info:
                print(f"   大小: {file_info['size']} 字节")
                print(f"   修改时间: {file_info['last_modified']}")
            else:
                print("   无法获取文件信息")
        except Exception as e:
            print(f"❌ 获取文件信息失败: {str(e)}")

        # 下载文件
        download_filename = f"downloaded_{test_filename}"
        print(f"📥 下载文件到: {download_filename}")

        try:
            download_success = storage_manager.download_file(remote_path, download_filename)
            if download_success:
                print("✅ 文件下载成功")

                # 验证文件内容
                with open(download_filename, 'r', encoding='utf-8') as f:
                    content = f.read()

                if test_content in content:
                    print("✅ 文件内容验证成功")
                else:
                    print("❌ 文件内容验证失败")
            else:
                print("❌ 文件下载失败")
        except Exception as e:
            print(f"⚠️  下载失败: {str(e)}")

        # 删除测试文件
        print(f"🗑️  删除测试文件")
        try:
            # 删除云存储中的文件
            delete_success = storage_manager.delete_file(remote_path)
            if delete_success:
                print("✅ 云存储文件删除成功")

            # 删除本地测试文件
            if os.path.exists(test_filename):
                os.remove(test_filename)
                print(f"✅ 本地测试文件删除成功: {test_filename}")

            if os.path.exists(download_filename):
                os.remove(download_filename)
                print(f"✅ 本地下载文件删除成功: {download_filename}")

        except Exception as e:
            print(f"⚠️  删除文件时出错: {str(e)}")

        print_section("6. 演示备份管理器")
        try:
            backup_manager = CloudBackupManager(loaded_config['provider'], loaded_config['config'])
            print("✅ 备份管理器初始化成功")

            # 列出备份
            backups = backup_manager.list_backups()
            print(f"📋 当前备份数量: {len(backups)}")

            if backups:
                print("最近的备份:")
                for backup in backups[:3]:
                    print(f"   • {backup['name']} ({backup['type']}) - {backup['size']} 字节")
            else:
                print("   暂无备份文件")

        except Exception as e:
            print(f"⚠️  备份管理器演示失败: {str(e)}")

        print_section("7. 演示完成")
        print("🎉 云存储功能演示完成！")
        print("\n💡 下一步操作:")
        print("1. 配置您的云服务访问凭证")
        print("2. 修改 cloud_config.json 文件")
        print("3. 运行实际的数据备份操作")
        print("4. 集成到您的考勤系统中")

    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保所有依赖包已安装:")
        print("pip install boto3 google-cloud-storage azure-storage-blob")
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")

def demo_api_usage():
    """演示API使用"""
    print_header("API使用演示")

    try:
        from flask import Flask, jsonify

        print_section("Flask API集成示例")

        api_code = '''
from flask import Flask, request, jsonify
from cloud_integration import enable_cloud_storage

app = Flask(__name__)

# 启用云存储功能
enable_cloud_storage(app)

@app.route('/')
def home():
    return "人脸考勤系统 - 云存储已启用"

# 云存储API端点
@app.route('/cloud/status')
def cloud_status():
    """获取云存储状态"""
    return jsonify({"success": True, "message": "云存储已连接"})

@app.route('/cloud/backup/database', methods=['POST'])
def backup_database():
    """备份数据库"""
    # 云存储会自动处理
    return jsonify({"success": True, "message": "数据库备份完成"})

@app.route('/cloud/backup/all', methods=['POST'])
def backup_all():
    """备份所有数据"""
    return jsonify({"success": True, "message": "完整备份完成"})

if __name__ == '__main__':
    app.run(debug=True)
'''

        print("📝 Flask API集成代码:")
        print(api_code)

        print_section("API测试命令")
        print("测试云存储状态:")
        print("  curl http://localhost:5000/cloud/status")

        print("备份数据库:")
        print("  curl -X POST http://localhost:5000/cloud/backup/database")

        print("备份所有数据:")
        print("  curl -X POST http://localhost:5000/cloud/backup/all")

    except Exception as e:
        print(f"❌ API演示失败: {e}")

def demo_environment_setup():
    """演示环境设置"""
    print_header("环境设置演示")

    print_section("1. 环境变量配置")

    env_content = '''# 复制此内容到 .env 文件
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET_NAME=face-attendance-backup-your-unique-name
'''

    print("📝 .env 文件内容:")
    print(env_content)

    print_section("2. 依赖安装")

    pip_commands = [
        "pip install boto3",           # AWS S3支持
        "pip install google-cloud-storage",  # Google Cloud支持
        "pip install azure-storage-blob",    # Azure支持
        "pip install flask",          # Web框架
        "pip install python-dotenv"  # 环境变量管理
    ]

    for cmd in pip_commands:
        print(f"   {cmd}")

    print_section("3. AWS S3 配置步骤")

    aws_steps = [
        "1. 访问 https://aws.amazon.com/free/",
        "2. 注册AWS账户（需要信用卡，仅用于验证身份）",
        "3. 登录AWS管理控制台",
        "4. 进入S3服务",
        "5. 创建存储桶（名称必须全局唯一）",
        "6. 进入IAM服务，创建用户",
        "7. 为用户添加S3权限",
        "8. 获取Access Key和Secret Key",
        "9. 将密钥添加到环境变量或.env文件中"
    ]

    for step in aws_steps:
        print(f"   {step}")

    print_section("4. 测试配置")

    test_code = '''
# 测试AWS S3连接
import boto3
try:
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    print("✅ AWS S3 连接成功")
    print(f"存储桶数量: {len(response['Buckets'])}")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("请检查您的AWS凭证配置")
'''

    print("📝 测试脚本:")
    print(test_code)

def main():
    """主演示函数"""
    print("🚀 云存储功能演示")
    print("这个演示将展示云存储的完整功能")

    # 检查是否在正确的目录
    if not os.path.exists('cloud_config.py'):
        print("❌ 请在正确的目录运行此脚本")
        return

    # 运行演示
    demo_cloud_storage()
    demo_api_usage()
    demo_environment_setup()

    print_header("演示总结")
    print("🎯 这个演示展示了以下功能:")
    print("   ✅ 云服务提供商配置")
    print("   ✅ 文件上传下载")
    print("   ✅ 列出和删除文件")
    print("   ✅ 备份管理")
    print("   ✅ Flask API集成")
    print("   ✅ 环境变量配置")

    print("\n📚 更多信息请查看:")
    print("   • README_CLOUD.md")
    print("   • SECURITY_FIXES.md")
    print("   • cloud_config.py")
    print("   • cloud_integration.py")

    print("\n🎉 演示完成！现在您可以开始使用云存储功能了。")

if __name__ == "__main__":
    main()