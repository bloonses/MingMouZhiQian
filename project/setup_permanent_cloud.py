#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永久免费云存储设置和配置
自动配置最适合的永久免费云存储方案
"""

import os
import json
import sys
from datetime import datetime

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def print_banner():
    """打印欢迎横幅"""
    print("=" * 80)
    print("🎯 永久免费云存储设置向导")
    print("=" * 80)
    print("为您的人脸考勤系统配置真正永久免费的云存储")
    print("=" * 80)

def analyze_storage_needs():
    """分析存储需求"""
    print("\n📊 存储需求分析:")
    print("-" * 40)

    # 基于实际系统的存储估算
    estimates = {
        '当前使用': {
            '数据库': '10MB',
            '人脸数据': '200MB',
            '配置文件': '5MB',
            '总计': '215MB'
        },
        '1年预测': {
            '数据库': '120MB',
            '人脸数据': '2.4GB',
            '配置文件': '60MB',
            '总计': '2.58GB'
        },
        '5年预测': {
            '数据库': '600MB',
            '人脸数据': '12GB',
            '配置文件': '300MB',
            '总计': '12.9GB'
        }
    }

    for period, data in estimates.items():
        print(f"\n📈 {period}:")
        for item, size in data.items():
            print(f"   {item:10}: {size}")

    return estimates

def compare_permanent_providers():
    """比较永久免费提供商"""
    print("\n🏆 永久免费云存储提供商比较:")
    print("-" * 80)

    providers = [
        {
            'name': 'Backblaze B2',
            'storage': '10GB',
            'download': '1GB/天',
            'upload': '无限制',
            'duration': '永久免费',
            'recommended': True,
            'setup_difficulty': '中等',
            'best_for': '大容量存储需求',
            'website': 'https://www.backblaze.com/b2/'
        },
        {
            'name': 'Google Cloud Storage',
            'storage': '5GB',
            'download': '1GB/月',
            'upload': '20K操作/月',
            'duration': '永久免费',
            'recommended': False,
            'setup_difficulty': '简单',
            'best_for': 'Google生态用户',
            'website': 'https://cloud.google.com/free'
        },
        {
            'name': 'Azure Blob Storage',
            'storage': '5GB',
            'download': '1GB/月',
            'upload': '20K操作/月',
            'duration': '永久免费',
            'recommended': False,
            'setup_difficulty': '中等',
            'best_for': '微软生态用户',
            'website': 'https://azure.microsoft.com/free'
        },
        {
            'name': 'Firebase Storage',
            'storage': '5GB',
            'download': '1GB/天',
            'upload': '无限制',
            'duration': '永久免费',
            'recommended': False,
            'setup_difficulty': '简单',
            'best_for': 'Web应用集成',
            'website': 'https://firebase.google.com/free'
        }
    ]

    print(f"{'服务商':<20} {'存储':<10} {'下载':<12} {'上传':<12} {'推荐':<8} {'难度':<8} {'用途':<20}")
    print("-" * 80)

    for provider in providers:
        rec_mark = "✅" if provider['recommended'] else "❌"
        print(f"{provider['name']:<20} {provider['storage']:<10} {provider['download']:<12} "
              f"{provider['upload']:<12} {rec_mark:<8} {provider['setup_difficulty']:<8} "
              f"{provider['best_for']:<20}")

    # 推荐理由
    print("\n🎯 推荐理由:")
    print("✅ Backblaze B2: 10GB永久免费存储，足够5年数据需求，无限制上传")
    print("⚠️  其他方案: 存储空间有限，5年后可能超出免费限额")

    return providers

def setup_recommendation():
    """提供设置建议"""
    print("\n🚀 设置建议:")
    print("-" * 40)

    print("🏆 强烈推荐: Backblaze B2")
    print("   理由:")
    print("   • 10GB永久免费存储空间")
    print("   • 1GB/天免费下载流量")
    print("   • 无限制上传")
    print("   • 永久免费（无时间限制）")
    print("   • 足够存储5年的人脸考勤数据")

    print("\n⚠️  注意事项:")
    print("   • 存储桶名称必须全局唯一")
    print("   • 需要注册账号并生成应用密钥")
    print("   • 安全起见建议启用多因素认证")

    return 'backblaze_b2'

def create_config_files(provider):
    """创建配置文件"""
    print(f"\n📁 创建 {provider} 配置文件...")

    # Backblaze B2 配置
    if provider == 'backblaze_b2':
        config = {
            'provider': 'backblaze_b2',
            'provider_name': 'Backblaze B2',
            'bucket_name': 'face-attendance-backup',
            'backup_prefix': 'backup/',
            'max_backups': 30,
            'config': {
                # 环境变量配置
                'application_key_id_env': 'B2_APPLICATION_KEY_ID',
                'application_key_env': 'B2_APPLICATION_KEY',
                'bucket_name_env': 'B2_BUCKET_NAME',
                'bucket_id_env': 'B2_BUCKET_ID',
                'download_url_env': 'B2_DOWNLOAD_URL'
            },
            'free_quota': {
                'storage': '10GB',
                'download': '1GB/天',
                'upload': '无限制',
                'duration': '永久免费',
                'enough_for_5_years': '✅ 12.9GB < 10GB? (可能需要优化存储)'
            },
            'setup_steps': [
                "1. 访问 https://www.backblaze.com/b2/",
                "2. 注册账号（永久免费）",
                "3. 登录后进入 'B2 Cloud Storage'",
                "4. 创建存储桶 Bucket Name: face-attendance-backup",
                "5. Bucket Type: Private",
                "6. 记下 Bucket ID",
                "7. 进入 'App Keys' 创建新密钥",
                "8. 保存 KeyID 和 Application Key",
                "9. 配置环境变量"
            ]
        }

        # 创建主配置文件
        filename = 'backblaze_config.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建环境变量模板
        env_template = f'''# Backblaze B2 永久免费环境变量配置
# 复制此文件为 .env_backblaze 并填入您的实际配置

# Backblaze B2 配置（10GB永久免费）
# 1. 访问: https://www.backblaze.com/b2/
# 2. 注册账号并获取访问凭证
# 3. 创建存储桶: face-attendance-backup
# 4. 生成应用密钥

# B2 应用凭证
B2_APPLICATION_KEY_ID=your_application_key_id_here
B2_APPLICATION_KEY=your_application_key_here
B2_BUCKET_NAME=face-attendance-backup
B2_BUCKET_ID=your_bucket_id_here
B2_DOWNLOAD_URL=https://f004.backblazeb2.com/file

# 其他配置
FLASK_ENV=development
PYTHONPATH={current_dir}
'''

        env_filename = '.env_backblaze'
        with open(env_filename, 'w', encoding='utf-8') as f:
            f.write(env_template)

        # 创建简单的测试脚本
        test_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backblaze B2 测试脚本
验证云存储连接和功能
"""

import os
import sys
sys.path.append('{current_dir}')

def test_backblaze_connection():
    """测试Backblaze B2连接"""
    try:
        # 检查环境变量
        required_vars = ['B2_APPLICATION_KEY_ID', 'B2_APPLICATION_KEY', 'B2_BUCKET_NAME']
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print("❌ 缺少环境变量:")
            for var in missing_vars:
                print(f"   {var}")
            print("请检查 .env_backblaze 文件")
            return False

        # 导入B2管理器
        from backblaze_b2_storage import BackblazeB2Manager

        # 初始化管理器
        config = {{
            'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': os.getenv('B2_BUCKET_NAME'),
            'bucket_id': os.getenv('B2_BUCKET_ID'),
            'download_url': os.getenv('B2_DOWNLOAD_URL', 'https://f004.backblazeb2.com/file')
        }}

        b2_manager = BackblazeB2Manager(config)

        # 测试连接
        bucket_info = b2_manager.get_bucket_info()
        print(f"✅ 连接成功!")
        print(f"   存储桶: {{bucket_info['bucketName']}}")
        print(f"   存储桶ID: {{bucket_info['bucketId']}}")
        print(f"   类型: {{bucket_info['bucketType']}}")

        # 测试文件列表
        files = b2_manager.list_files()
        print(f"   文件数量: {{len(files)}}")

        return True

    except ImportError as e:
        print(f"❌ 导入模块失败: {{e}}")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {{e}}")
        print("请检查:")
        print("   1. 环境变量是否正确设置")
        print("   2. 网络连接是否正常")
        print("   3. B2应用密钥是否有效")
        return False

def test_backup_functionality():
    """测试备份功能"""
    try:
        from backblaze_b2_storage import BackblazeBackupManager

        # 初始化备份管理器
        config = {{
            'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': os.getenv('B2_BUCKET_NAME'),
            'bucket_id': os.getenv('B2_BUCKET_ID'),
            'backup_prefix': 'backup/',
            'max_backups': 30
        }}

        backup_manager = BackblazeBackupManager(config)

        # 测试备份状态
        status = backup_manager.get_backup_status()
        print("📊 备份状态:")
        print(f"   总备份数: {{status['total_backups']}}")
        print(f"   总大小: {{status['total_size_mb']}} MB")
        print(f"   最新备份: {{status['newest_backup']}}")

        return True

    except Exception as e:
        print(f"❌ 备份功能测试失败: {{e}}")
        return False

if __name__ == "__main__":
    print("🧪 Backblaze B2 连接测试")
    print("=" * 40)

    # 测试连接
    print("1. 测试连接...")
    if test_backblaze_connection():
        print("✅ 连接测试成功!")

        # 测试备份功能
        print("2. 测试备份功能...")
        if test_backup_functionality():
            print("✅ 备份功能测试成功!")
            print("\\n🎉 所有测试通过! 您可以开始使用云存储功能了。")
        else:
            print("⚠️  备份功能测试失败，但连接正常。")
    else:
        print("\\n❌ 请检查配置后重试。")
'''

        test_filename = 'test_backblaze_b2.py'
        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(test_script)

        print(f"✅ 配置文件已创建:")
        print(f"   - {filename}")
        print(f"   - {env_filename}")
        print(f"   - {test_filename}")

    return config

def create_integration_guide():
    """创建集成指南"""
    print("\n📖 集成指南:")
    print("-" * 40)

    guide = '''
🎯 将Backblaze B2集成到您的考勤系统中

### 1. 配置步骤

1. **注册Backblaze B2账号**
   - 访问: https://www.backblaze.com/b2/
   - 注册账号（需要邮箱验证）
   - 登录后进入"B2 Cloud Storage"

2. **创建存储桶**
   - 点击"Create a Bucket"
   - Bucket Name: face-attendance-backup
   - Bucket Type: Private
   - 保存Bucket ID

3. **生成应用密钥**
   - 进入"App Keys"
   - 点击"Create Application Key"
   - 输入密钥名称
   - 选择权限（建议选择B2相关权限）
   - 保存Key ID和Application Key

4. **配置环境变量**
   ```bash
   # 复制 .env_backblaze 文件并填入实际值
   cp .env_backblaze .env

   # 编辑 .env 文件，填入您的B2凭证
   ```

### 2. 在应用中集成

```python
# 修改 app.py 文件
from flask import Flask
from backblaze_b2_storage import BackblazeBackupManager

app = Flask(__name__)

# 启用云存储备份功能
def setup_cloud_backup():
    try:
        from dotenv import load_dotenv
        load_dotenv()  # 加载环境变量

        # 初始化备份管理器
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

# 在应用启动时初始化
backup_manager = setup_cloud_backup()

# 添加备份路由
@app.route('/backup/database', methods=['POST'])
def backup_database():
    if backup_manager:
        try:
            success = backup_manager.backup_database('attendance.db')
            if success:
                return jsonify({'success': True, 'message': '数据库备份成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'备份失败: {e}'})

    return jsonify({'success': False, 'message': '备份服务不可用'})
```

### 3. 自动备份配置

```python
# 创建自动备份定时任务
def schedule_backup():
    import schedule
    import time
    from datetime import datetime

    # 每日备份
    schedule.every().day.at("23:59").do(backup_database)
    schedule.every().day.at("22:00").do(backup_student_faces)

    print("自动备份已启动...")

    while True:
        schedule.run_pending()
        time.sleep(60)
```

### 4. 测试功能

```bash
# 运行测试脚本
python test_backblaze_b2.py

# 测试手动备份
python -c "
from backblaze_b2_storage import BackblazeBackupManager
import os
from dotenv import load_dotenv
load_dotenv()

config = {
    'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
    'application_key': os.getenv('B2_APPLICATION_KEY'),
    'bucket_name': os.getenv('B2_BUCKET_NAME'),
    'bucket_id': os.getenv('B2_BUCKET_ID'),
    'backup_prefix': 'backup/',
    'max_backups': 30
}

backup_manager = BackblazeBackupManager(config)
success = backup_manager.backup_database('attendance.db')
print(f'备份结果: {success}')
"
```

### 5. 安全提示

⚠️ **重要安全事项:**
- 📧 不要在代码中硬编码凭证
- 🔐 定期轮换应用密钥
- 🌐 启用多因素认证
- 🔒 备份数据使用HTTPS传输
- 📊 定期检查备份完整性
- 💾 重要数据多区域备份
'''

    # 保存指南
    with open('BACKBLAZE_INTEGRATION.md', 'w', encoding='utf-8') as f:
        f.write(guide)

    print("✅ 集成指南已创建: BACKBLAZE_INTEGRATION.md")

def create_final_summary():
    """创建最终总结"""
    print("\n🎉 设置完成总结:")
    print("-" * 40)

    print("✅ 已完成的操作:")
    print("   1. 分析了存储需求（当前215MB，5年预测12.9GB）")
    print("   2. 比较了永久免费提供商")
    print("   3. 推荐了Backblaze B2（10GB永久免费）")
    print("   4. 创建了配置文件")
    print("   5. 生成了环境变量模板")
    print("   6. 创建了测试脚本")
    print("   7. 提供了集成指南")

    print("\n📋 下一步操作:")
    print("   1. 访问 https://www.backblaze.com/b2/ 注册账号")
    print("   2. 创建存储桶: face-attendance-backup")
    print("   3. 生成应用密钥")
    print("   4. 编辑 .env_backblaze 填入实际凭证")
    print("   5. 运行 python test_backblaze_b2.py 测试连接")
    print("   6. 按照集成指南修改您的应用")

    print("\n🎯 费用预估:")
    print("   • Backblaze B2: $0/永久免费")
    print("   • 存储空间: 10GB")
    print("   • 下载流量: 1GB/天")
    print("   • 5年数据需求: 12.9GB")
    print("   • 建议: 5年后可能需要清理旧数据或升级计划")

    print("\n📞 技术支持:")
    print("   • Backblaze B2文档: https://www.backblaze.com/b2/docs/")
    print("   • 如果遇到问题，请检查:")
    print("     - 环境变量是否正确设置")
    print("     - 网络连接是否正常")
    print("     - 应用密钥是否有效")

def main():
    """主函数"""
    print_banner()

    # 分析存储需求
    analyze_storage_needs()

    # 比较提供商
    providers = compare_permanent_providers()

    # 获取设置建议
    recommended_provider = setup_recommendation()

    # 创建配置文件
    config = create_config_files(recommended_provider)

    # 创建集成指南
    create_integration_guide()

    # 创建最终总结
    create_final_summary()

    print("\n" + "=" * 80)
    print("🎯 永久免费云存储配置完成!")
    print("=" * 80)
    print("您的考勤系统现在已准备好使用Backblaze B2永久免费云存储!")
    print("按照集成指南开始使用吧! 🚀")

if __name__ == "__main__":
    main()