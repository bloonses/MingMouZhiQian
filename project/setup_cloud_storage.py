"""
云存储设置脚本 - 快速配置云存储功能
"""

import os
import sys
import subprocess
from cloud_config import CloudStorageConfig, setup_guide, FreeTierInfo

def check_dependencies():
    """检查依赖包"""
    required_packages = {
        'boto3': 'AWS S3支持',
        'google-cloud-storage': 'Google Cloud Storage支持',
        'azure-storage-blob': 'Azure Blob Storage支持',
        'flask': 'Web框架'
    }

    missing_packages = []

    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 未安装 ({description})")
            missing_packages.append(package)

    return missing_packages

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package} 安装失败")
        return False

def create_sample_app():
    """创建示例应用代码"""
    app_code = '''
# app.py - 示例云存储集成代码

from flask import Flask
from cloud_integration import enable_cloud_storage

app = Flask(__name__)

# 基础配置
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['UPLOAD_FOLDER'] = 'static'

# 启用云存储功能
enable_cloud_storage(app)

# 基本路由
@app.route('/')
def home():
    return "人脸考勤系统已启用云存储功能"

# 云存储API测试
@app.route('/cloud/test')
def cloud_test():
    return "云存储功能已集成"

if __name__ == '__main__':
    app.run(debug=True)
'''

    with open('app_with_cloud.py', 'w', encoding='utf-8') as f:
        f.write(app_code)

    print("✅ 示例应用已创建: app_with_cloud.py")

def create_usage_example():
    """创建使用示例"""
    example_code = '''
# cloud_usage_example.py - 云存储使用示例

from cloud_storage import setup_cloud_storage, CloudBackupManager
from cloud_config import CloudStorageConfig

# 1. 初始化云存储
config = CloudStorageConfig.load_config('cloud_config.json')
storage_manager = setup_cloud_storage(config['provider'], config['config'])

# 2. 备份数据库
backup_manager = CloudBackupManager(config['provider'], config['config'])

# 备份数据库
success = backup_manager.backup_database('attendance.db')
if success:
    print("数据库备份成功")
else:
    print("数据库备份失败")

# 备份学生人脸数据
success = backup_manager.backup_student_faces('static/faces')
if success:
    print("人脸数据备份成功")
else:
    print("人脸数据备份失败")

# 3. 列出备份
backups = backup_manager.list_backups()
print(f"共 {len(backups)} 个备份:")
for backup in backups:
    print(f"- {backup['name']} ({backup['type']})")

# 4. 恢复数据库
backup_name = 'database_backup_20240101_120000.db'
success = backup_manager.restore_database(f'backup/{backup_name}', 'restored_database.db')
if success:
    print("数据库恢复成功")
else:
    print("数据库恢复失败")

# 5. 文件上传下载
# 上传文件
success = storage_manager.upload_file('local_file.txt', 'backup/local_file.txt')
if success:
    print("文件上传成功")

# 下载文件
success = storage_manager.download_file('backup/local_file.txt', 'downloaded_file.txt')
if success:
    print("文件下载成功")

# 列出文件
files = storage_manager.list_files('backup/')
print(f"备份文件夹中的文件: {files}")
'''

    with open('cloud_usage_example.py', 'w', encoding='utf-8') as f:
        f.write(example_code)

    print("✅ 使用示例已创建: cloud_usage_example.py")

def create_environment_template():
    """创建环境变量模板"""
    env_template = '''# 云存储环境变量配置模板
# 复制此文件为 .env 并填入您的实际配置

# ===========================================
# AWS S3 配置（推荐初学者使用）
# ===========================================
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET_NAME=face-attendance-backup-your-unique-name

# ===========================================
# Google Cloud Storage 配置
# ===========================================
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
GOOGLE_PROJECT_ID=your-google-project-id

# ===========================================
# Azure Blob Storage 配置
# ===========================================
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string_here
AZURE_STORAGE_ACCOUNT_NAME=your_account_name
AZURE_STORAGE_ACCOUNT_KEY=your_account_key

# ===========================================
# 其他配置
# ===========================================
FLASK_ENV=development
FLASK_DEBUG=1
'''

    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_template)

    print("✅ 环境变量模板已创建: .env.example")

def setup_complete_guide():
    """设置完成指南"""
    print("\n" + "=" * 60)
    print("🎯 云存储设置完成指南")
    print("=" * 60)

    print("\n📋 已完成的设置:")
    print("1. ✅ 创建了云存储配置文件")
    print("2. ✅ 添加了云存储集成模块")
    print("3. ✅ 创建了示例应用代码")
    print("4. ✅ 生成了使用示例")
    print("5. ✅ 配置了环境变量模板")

    print("\n🚀 下一步操作:")
    print("1. 选择云服务提供商并注册账号")
    print("2. 创建配置文件并填入您的凭证")
    print("3. 安装必要的依赖包")
    print("4. 测试云存储连接")
    print("5. 启用云存储功能")

    print("\n💡 推荐的设置步骤:")
    print("1. 运行 'python cloud_config.py' 查看详细设置指南")
    print("2. 注册AWS账号并获取S3访问凭证")
    print("3. 修改 cloud_config.json 文件")
    print("4. 运行 'python cloud_usage_example.py' 测试功能")
    print("5. 将云存储集成到您的应用中")

def main():
    """主函数"""
    print("🚀 开始配置云存储功能...")

    # 显示设置指南
    print("\n" + "=" * 60)
    setup_guide()
    print("=" * 60)

    # 检查依赖
    print("\n🔍 检查依赖包...")
    missing = check_dependencies()

    if missing:
        print(f"\n⚠️  发现 {len(missing)} 个缺失的依赖包")
        choice = input(f"是否自动安装缺失的包 {missing}? (y/n): ").lower().strip()

        if choice == 'y':
            for package in missing:
                if package == 'flask':
                    print("注意: Flask 是必需的Web框架包")
                if package in ['google-cloud-storage', 'azure-storage-blob']:
                    print(f"注意: {package} 是可选的，用于特定云服务支持")

                install_package(package)
        else:
            print("请手动安装缺失的包:")
            for package in missing:
                print(f"  pip install {package}")

    # 创建文件
    print("\n📁 创建示例文件...")
    create_sample_app()
    create_usage_example()
    create_environment_template()

    # 显示完成指南
    setup_complete_guide()

    print("\n🎉 云存储设置完成！")
    print("请按照指南选择云服务提供商并配置访问凭证")

if __name__ == "__main__":
    main()