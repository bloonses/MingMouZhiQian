#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B2云存储配置助手 - 交互式设置工具
"""

import os
import sys
import json
import subprocess
from datetime import datetime

def print_step(step_number, title, description):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_number}: {title}")
    print(f"{'='*60}")
    print(description)

def get_confirmation(prompt):
    """获取用户确认"""
    while True:
        response = input(f"\n{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes', '是']:
            return True
        elif response in ['n', 'no', '否']:
            return False
        else:
            print("请输入 y/n 或 yes/no")

def check_python_dependencies():
    """检查Python依赖"""
    print_step(1, "检查Python依赖", "检查必要的Python包是否已安装")

    required_packages = {
        'boto3': 'AWS S3支持（用于测试）',
        'python-dotenv': '环境变量管理',
        'requests': 'HTTP请求库'
    }

    missing_packages = []

    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 未安装 ({description})")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n发现 {len(missing_packages)} 个缺失的包:")
        install_choice = get_confirmation("是否自动安装缺失的包？")

        if install_choice:
            for package in missing_packages:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    print(f"✅ {package} 安装成功")
                except subprocess.CalledProcessError:
                    print(f"❌ {package} 安装失败")
                    print(f"请手动安装: pip install {package}")
        else:
            print("请手动安装缺失的包:")
            for package in missing_packages:
                print(f"  pip install {package}")

    return len(missing_packages) == 0

def create_environment_files():
    """创建环境变量文件"""
    print_step(2, "创建环境变量文件", "创建B2配置所需的环境变量文件")

    # 检查是否已存在环境文件
    env_files = ['.env', '.env.local', '.env_backblaze']
    existing_files = [f for f in env_files if os.path.exists(f)]

    if existing_files:
        print(f"发现现有环境文件: {', '.join(existing_files)}")
        overwrite = get_confirmation("是否覆盖现有文件？")
        if not overwrite:
            print("跳过环境文件创建")
            return True

    # 创建环境变量文件
    env_content = '''# Backblaze B2 永久免费环境变量配置
# 复制此文件为 .env 并填入您的实际配置

# ===========================================
# Backblaze B2 配置（10GB永久免费）
# ===========================================
# 1. 访问 https://www.backblaze.com/b2/
# 2. 注册账号并获取访问凭证
# 3. 创建存储桶: face-attendance-backup
# 4. 生成应用密钥

# B2 应用凭证 (请填入您的实际值)
B2_APPLICATION_KEY_ID=your_application_key_id_here
B2_APPLICATION_KEY=your_application_key_here
B2_BUCKET_NAME=face-attendance-backup
B2_BUCKET_ID=your_bucket_id_here
B2_DOWNLOAD_URL=https://f004.backblazeb2.com/file

# ===========================================
# 应用配置
# ===========================================
FLASK_ENV=development
PYTHONPATH={current_dir}
'''

    env_filename = '.env'
    with open(env_filename, 'w', encoding='utf-8') as f:
        f.write(env_content.replace('{current_dir}', os.path.dirname(os.path.abspath(__file__))))

    print(f"✅ 环境变量文件已创建: {env_filename}")
    print("📝 请编辑此文件并填入您的B2凭证")

    return True

def generate_setup_checklist():
    """生成设置检查清单"""
    print_step(3, "生成设置检查清单", "创建Backblaze B2设置的完整检查清单")

    checklist_content = '''# 🎯 Backblaze B2 设置检查清单

## ✅ 准备阶段
- [ ] 访问 https://www.backblaze.com/b2/
- [ ] 注册邮箱账号
- [ ] 验证邮箱
- [ ] 登录B2 Cloud Storage

## ✅ 存储桶设置
- [ ] 创建存储桶
- [ ] Bucket Name: face-attendance-backup
- [ ] Bucket Type: Private
- [ ] 记录 Bucket ID

## ✅ 应用密钥设置
- [ ] 进入 App Keys
- [ ] 点击 Create Application Key
- [ Key Name: face-attendance-app
- [ 选择 B2 相关权限
- [ ] 保存 Key ID 和 Application Key

## ✅ 环境变量配置
- [ ] 编辑 .env 文件
- [ ] 填入 B2_APPLICATION_KEY_ID
- [ ] 填入 B2_APPLICATION_KEY
- [ ] 填入 B2_BUCKET_ID
- [ ] 保存文件

## ✅ 测试验证
- [ ] 运行 python test_b2_connection.py
- [ ] 确认连接成功
- [ ] 测试文件上传下载
- [ ] 测试备份功能

## ⚠️ 重要提醒
- 📧 Key ID 和 Application Key 只能显示一次，请务必保存
- 🔐 启用账号的多因素认证
- 🔄 定期轮换应用密钥
- 💾 重要数据多重备份

## 📞 联系支持
如果遇到问题：
- 查看官方文档: https://www.backblaze.com/b2/docs/
- 检查网络连接
- 验证密钥权限
'''

    checklist_filename = 'B2_SETUP_CHECKLIST.md'
    with open(checklist_filename, 'w', encoding='utf-8') as f:
        f.write(checklist_content)

    print(f"✅ 设置检查清单已创建: {checklist_filename}")
    return True

def create_connection_test():
    """创建连接测试脚本"""
    print_step(4, "创建连接测试脚本", "创建B2连接测试工具")

    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B2连接测试脚本
验证B2云存储配置是否正确
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def check_environment():
    """检查环境变量"""
    logger = setup_logging()

    print("🔍 检查环境变量...")

    # 加载环境变量
    load_dotenv()

    required_vars = [
        'B2_APPLICATION_KEY_ID',
        'B2_APPLICATION_KEY',
        'B2_BUCKET_NAME',
        'B2_BUCKET_ID'
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value and value != f'your_{var.lower().replace("_", "_")}_here':
            print(f"✅ {var}: 已设置")
        else:
            print(f"❌ {var}: 未设置或使用默认值")
            missing_vars.append(var)

    if missing_vars:
        print(f"\\n⚠️  缺少 {len(missing_vars)} 个环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\\n请编辑 .env 文件并填入正确的值")
        return False

    return True

def test_backblaze_connection():
    """测试Backblaze B2连接"""
    logger = setup_logging()

    try:
        # 尝试导入B2管理器
        from backblaze_b2_storage import BackblazeB2Manager

        print("🔄 正在连接到Backblaze B2...")

        # 获取配置
        config = {
            'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': os.getenv('B2_BUCKET_NAME'),
            'bucket_id': os.getenv('B2_BUCKET_ID'),
            'download_url': os.getenv('B2_DOWNLOAD_URL', 'https://f004.backblazeb2.com/file')
        }

        # 初始化管理器
        b2_manager = BackblazeB2Manager(config)

        # 测试连接
        print("🔍 获取存储桶信息...")
        bucket_info = b2_manager.get_bucket_info()

        print("✅ 连接成功!")
        print(f"   存储桶名称: {bucket_info['bucketName']}")
        print(f"   存储桶ID: {bucket_info['bucketId']}")
        print(f"   存储桶类型: {bucket_info['bucketType']}")

        # 测试文件列表
        print("📋 测试文件列表...")
        files = b2_manager.list_files()
        print(f"   文件数量: {len(files)}")

        # 测试文件上传
        print("📤 测试文件上传...")
        test_filename = "b2_test_file.txt"
        test_content = f"测试文件\\n时间: {datetime.now().isoformat()}\\n这是连接测试文件"

        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(test_content)

        upload_success = b2_manager.upload_file(test_filename, f"test/{test_filename}")
        if upload_success:
            print("✅ 文件上传成功")

            # 测试文件下载
            print("📥 测试文件下载...")
            download_filename = f"downloaded_{test_filename}"
            download_success = b2_manager.download_file(f"test/{test_filename}", download_filename)

            if download_success:
                print("✅ 文件下载成功")

                # 清理测试文件
                try:
                    os.remove(test_filename)
                    os.remove(download_filename)
                    print("✅ 测试文件清理完成")
                except:
                    pass

                # 删除云存储中的测试文件
                try:
                    b2_manager.delete_file(f"test/{test_filename}")
                    print("✅ 云存储测试文件删除完成")
                except:
                    pass

                return True
            else:
                print("❌ 文件下载失败")
                return False
        else:
            print("❌ 文件上传失败")
            return False

    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保 backblaze_b2_storage.py 模块存在")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        print("请检查:")
        print("   1. 环境变量是否正确设置")
        print("   2. 网络连接是否正常")
        print("   3. B2应用密钥是否有效")
        print("   4. 存储桶是否存在")
        return False

def main():
    """主函数"""
    print("🧪 Backblaze B2 连接测试")
    print("=" * 50)

    # 检查环境变量
    if not check_environment():
        print("\\n❌ 环境变量检查失败，请先配置 .env 文件")
        return False

    # 测试连接
    if test_backblaze_connection():
        print("\\n🎉 所有测试通过! B2云存储配置成功!")
        print("\\n🚀 您可以开始使用云存储功能了!")
        return True
    else:
        print("\\n❌ 测试失败，请检查配置后重试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''

    test_filename = 'test_b2_connection.py'
    with open(test_filename, 'w', encoding='utf-8') as f:
        f.write(test_script)

    print(f"✅ 连接测试脚本已创建: {test_filename}")
    return True

def create_integration_example():
    """创建集成示例"""
    print_step(5, "创建集成示例", "创建B2集成到应用的示例代码")

    example_code = '''# app_integration_example.py
# B2云存储集成示例代码

import os
from flask import Flask, jsonify, request
from backblaze_b2_storage import BackblazeBackupManager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

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
        print(f"云存储初始化失败: {e}")
        return None

# 初始化备份管理器
backup_manager = setup_cloud_backup()

@app.route('/')
def home():
    return "人脸考勤系统 - B2云存储已集成"

@app.route('/cloud/status')
def cloud_status():
    """获取云存储状态"""
    if backup_manager:
        try:
            status = backup_manager.get_backup_status()
            return jsonify({
                'success': True,
                'message': '云存储连接正常',
                'status': status
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取状态失败: {e}'
            })
    else:
        return jsonify({
            'success': False,
            'message': '云存储服务未初始化'
        })

@app.route('/backup/database', methods=['POST'])
def backup_database():
    """备份数据库"""
    if not backup_manager:
        return jsonify({'success': False, 'message': '云存储服务不可用'})

    try:
        success = backup_manager.backup_database('attendance.db')
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
        return jsonify({'success': False, 'message': '云存储服务不可用'})

    try:
        success = backup_manager.backup_student_faces('static/faces')
        if success:
            return jsonify({'success': True, 'message': '人脸数据备份成功'})
        else:
            return jsonify({'success': False, 'message': '人脸数据备份失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'备份失败: {e}'})

@app.route('/list/backups')
def list_backups():
    """列出所有备份"""
    if not backup_manager:
        return jsonify({'success': False, 'message': '云存储服务不可用'})

    try:
        backups = backup_manager.list_backups()
        return jsonify({
            'success': True,
            'backups': backups,
            'count': len(backups)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取备份列表失败: {e}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''

    example_filename = 'app_integration_example.py'
    with open(example_filename, 'w', encoding='utf-8') as f:
        f.write(example_code)

    print(f"✅ 集成示例已创建: {example_filename}")
    return True

def show_next_steps():
    """显示下一步操作"""
    print_step(6, "下一步操作指南", "完成配置后的操作步骤")

    next_steps = '''
## 🚀 完成配置后的操作步骤：

### 1. 注册Backblaze B2账号
📍 访问: https://www.backblaze.com/b2/
📧 注册账号（需要邮箱验证）

### 2. 创建存储桶
🏷️ 进入 "B2 Cloud Storage"
➡️ 点击 "Create a Bucket"
📝 Bucket Name: face-attendance-backup
🔒 Bucket Type: Private
💾 保存Bucket ID

### 3. 生成应用密钥
🔑 进入 "App Keys"
➡️ 点击 "Create Application Key"
📝 Key Name: face-attendance-app
✅ 选择B2相关权限
💾 保存Key ID和Application Key（只能显示一次！）

### 4. 配置环境变量
📝 编辑 .env 文件
🔑 填入您的B2凭证
💾 保存文件

### 5. 测试连接
🧪 运行: python test_b2_connection.py
✅ 确认所有测试通过

### 6. 集成应用
📋 查看 app_integration_example.py
🔄 修改您的 app.py 文件
🚀 启动应用测试功能

## ⚠️ 重要提醒：
• Key ID和Application Key只能显示一次，请务必保存！
• 建议启用账号的多因素认证
• 定期检查备份完整性
'''

    print(next_steps)

    print("✅ 配置助手运行完成！")
    print("📁 已创建的文件:")
    print("   - .env (环境变量配置)")
    print("   - B2_SETUP_CHECKLIST.md (设置检查清单)")
    print("   - test_b2_connection.py (连接测试)")
    print("   - app_integration_example.py (集成示例)")

def main():
    """主函数"""
    print("🎯 B2云存储配置助手")
    print("This will help you configure Backblaze B2 cloud storage")
    print("=" * 60)

    # 检查依赖
    print("\n📋 步骤1/6: 检查Python依赖")
    if not check_python_dependencies():
        print("❌ 依赖检查失败，请先安装缺失的包")
        return

    # 创建环境文件
    print("\n📋 步骤2/6: 创建环境变量文件")
    if not create_environment_files():
        print("❌ 环境文件创建失败")
        return

    # 生成检查清单
    print("\n📋 步骤3/6: 生成设置检查清单")
    if not generate_setup_checklist():
        print("❌ 检查清单创建失败")
        return

    # 创建测试脚本
    print("\n📋 步骤4/6: 创建连接测试脚本")
    if not create_connection_test():
        print("❌ 测试脚本创建失败")
        return

    # 创建集成示例
    print("\n📋 步骤5/6: 创建集成示例")
    if not create_integration_example():
        print("❌ 集成示例创建失败")
        return

    # 显示下一步
    print("\n📋 步骤6/6: 显示下一步操作")
    show_next_steps()

if __name__ == "__main__":
    main()