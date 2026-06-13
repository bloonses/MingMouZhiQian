#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网一键启动脚本
自动检测网络环境，生成访问地址，启动系统
"""

import os
import sys
import socket
import subprocess
import webbrowser
import time
from datetime import datetime

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("🎯 校园网人脸考勤系统 - 一键启动")
    print("=" * 60)
    print("正在准备系统环境...")
    print("=" * 60)

def check_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")

    requirements = {
        'python_version': sys.version_info >= (3, 6),
        'flask_installed': check_package('flask'),
        'required_files': check_required_files(),
        'environment_config': check_env_config()
    }

    # 显示检查结果
    for item, status in requirements.items():
        if status:
            print(f"✅ {item}: 满足")
        else:
            print(f"❌ {item}: 不满足")

    # 检查是否所有要求都满足
    all_satisfied = all(requirements.values())
    if all_satisfied:
        print("✅ 所有系统要求已满足！")
    else:
        print("❌ 部分系统要求不满足，请先解决这些问题。")

    return all_satisfied

def check_package(package_name):
    """检查Python包是否安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def check_required_files():
    """检查必需文件是否存在"""
    required_files = [
        'app_campus.py',
        'backblaze_b2_storage.py',
        '.env'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"❌ 缺少文件: {', '.join(missing_files)}")

    return len(missing_files) == 0

def check_env_config():
    """检查环境变量配置"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        required_vars = [
            'B2_APPLICATION_KEY_ID',
            'B2_APPLICATION_KEY',
            'B2_BUCKET_NAME',
            'B2_BUCKET_ID'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")

        return len(missing_vars) == 0
    except Exception as e:
        print(f"❌ 环境配置检查失败: {e}")
        return False

def get_network_info():
    """获取网络信息"""
    print("🌐 获取网络信息...")

    try:
        # 获取本地IP地址
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        # 尝试获取公网IP
        try:
            result = subprocess.run(['curl', '-s', 'ifconfig.me'],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                public_ip = result.stdout.strip()
            else:
                public_ip = None
        except:
            public_ip = None

        network_info = {
            'local_ip': local_ip,
            'hostname': hostname,
            'public_ip': public_ip,
            'port': 5000,
            'access_urls': []
        }

        # 生成可能的访问URL
        access_urls = [
            f"http://{local_ip}:5000",
            f"http://localhost:5000",
        ]

        if public_ip:
            access_urls.append(f"http://{public_ip}:5000")

        network_info['access_urls'] = access_urls

        print(f"✅ 本地IP: {local_ip}")
        print(f"✅ 主机名: {hostname}")
        if public_ip:
            print(f"✅ 公网IP: {public_ip}")

        return network_info

    except Exception as e:
        print(f"❌ 获取网络信息失败: {e}")
        return None

def open_browser(urls):
    """打开浏览器"""
    print("🌐 打开浏览器...")

    # 选择第一个本地URL
    for url in urls:
        if url.startswith('http://localhost') or url.startswith('http://127.'):
            try:
                webbrowser.open(url)
                print(f"✅ 浏览器已打开: {url}")
                return True
            except:
                print(f"⚠️ 无法打开浏览器: {url}")
                return False

    return False

def generate_qr_code(urls):
    """生成二维码信息"""
    print("📱 生成二维码信息...")

    qr_info = []
    for i, url in enumerate(urls, 1):
        qr_info.append(f"{i}. {url}")

    return '\n'.join(qr_info)

def test_system_status():
    """测试系统状态"""
    print("🧪 测试系统状态...")

    try:
        # 测试端口是否可用
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()

        if result == 0:
            print("❌ 端口5000已被占用")
            return False
        else:
            print("✅ 端口5000可用")
            return True

    except Exception as e:
        print(f"❌ 端口测试失败: {e}")
        return False

def create_startup_script():
    """创建启动脚本"""
    print("📝 创建启动脚本...")

    script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网快速启动脚本
"""

import os
import sys

# 确保在正确的目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 检查Python版本
if sys.version_info < (3, 6):
    print("❌ 需要Python 3.6或更高版本")
    sys.exit(1)

try:
    # 启动系统
    from app_campus import app

    print("🚀 启动校园网访问版本...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

except Exception as e:
    print(f"❌ 启动失败: {e}")
    sys.exit(1)
'''

    with open('start_campus.py', 'w', encoding='utf-8') as f:
        f.write(script_content)

    print("✅ 启动脚本已创建: start_campus.py")

def show_usage_info(network_info, qr_code):
    """显示使用信息"""
    print("\n" + "=" * 60)
    print("🎯 系统已启动！")
    print("=" * 60)

    print("\n🌐 访问地址:")
    for i, url in enumerate(network_info['access_urls'], 1):
        print(f"   {i}. {url}")

    print("\n📱 二维码信息:")
    print(qr_code)

    print("\n📋 使用说明:")
    print("   1. 确保设备连接到校园网")
    print("   2. 使用以上任一地址访问系统")
    print("   3. 手机用户可以扫描二维码")
    print("   4. 默认管理员账户: admin / Admin@12345")

    print("\n🌟 系统功能:")
    print("   ✅ 人脸识别考勤")
    print("   ✅ 用户管理")
    print("   ✅ 课程管理")
    print("   ✅ 考勤记录")
    print("   ✅ B2云存储备份")
    print("   ✅ 网络诊断")

    print("\n📞 技术支持:")
    print("   如遇问题，请检查:")
    print("   1. 防火墙是否允许5000端口")
    print("   2. 是否连接到校园网")
    print("   3. 系统是否正常运行")

    print("\n" + "=" * 60)
    print("🎉 校园网用户现在可以访问系统了！")
    print("=" * 60)

def main():
    """主函数"""
    print_banner()

    # 检查系统要求
    if not check_requirements():
        print("\n❌ 系统要求不满足，请先解决这些问题。")
        return False

    # 获取网络信息
    network_info = get_network_info()
    if not network_info:
        print("\n❌ 无法获取网络信息。")
        return False

    # 测试系统状态
    if not test_system_status():
        print("\n❌ 端口被占用或无法访问。")
        return False

    # 生成二维码信息
    qr_code = generate_qr_code(network_info['access_urls'])

    # 创建启动脚本
    create_startup_script()

    # 显示使用信息
    show_usage_info(network_info, qr_code)

    # 询问是否立即启动
    while True:
        choice = input("\n是否立即启动系统？(y/n): ").strip().lower()
        if choice in ['y', 'yes', '是']:
            break
        elif choice in ['n', 'no', '否']:
            print("您稍后可以运行: python start_campus.py")
            return True
        else:
            print("请输入 y/n 或 yes/no")

    # 打开浏览器
    open_browser(network_info['access_urls'])

    print("\n🚀 启动系统...")
    print("按 Ctrl+C 停止系统")

    # 启动系统
    try:
        from app_campus import app
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n👋 系统已停止")
    except Exception as e:
        print(f"\n❌ 系统启动失败: {e}")
        return False

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)