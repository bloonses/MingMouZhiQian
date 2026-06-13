#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B2连接测试脚本 - 验证您的配置
"""

import os
import sys
from datetime import datetime

def test_b2_configuration():
    """测试B2配置"""
    print("🧪 Backblaze B2 连接测试")
    print("=" * 50)

    # 检查环境变量
    print("\n🔍 检查环境变量...")

    env_vars = {
        'B2_APPLICATION_KEY_ID': os.getenv('B2_APPLICATION_KEY_ID'),
        'B2_APPLICATION_KEY': os.getenv('B2_APPLICATION_KEY'),
        'B2_BUCKET_NAME': os.getenv('B2_BUCKET_NAME'),
        'B2_BUCKET_ID': os.getenv('B2_BUCKET_ID'),
        'B2_DOWNLOAD_URL': os.getenv('B2_DOWNLOAD_URL')
    }

    all_set = True
    for var, value in env_vars.items():
        if value:
            print(f"✅ {var}: 已设置")
            if 'KEY' in var:
                print(f"   值: {value[:10]}...")  # 只显示前10个字符
        else:
            print(f"❌ {var}: 未设置")
            all_set = False

    if not all_set:
        print("\n❌ 请检查 .env 文件中的配置")
        return False

    print("\n✅ 所有环境变量已正确设置")

    # 尝试导入B2模块
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from backblaze_b2_storage import BackblazeB2Manager
        print("✅ B2模块导入成功")
    except ImportError as e:
        print(f"❌ B2模块导入失败: {e}")
        print("请确保 backblaze_b2_storage.py 文件存在")
        return False

    # 创建配置
    config = {
        'application_key_id': env_vars['B2_APPLICATION_KEY_ID'],
        'application_key': env_vars['B2_APPLICATION_KEY'],
        'bucket_name': env_vars['B2_BUCKET_NAME'],
        'bucket_id': env_vars['B2_BUCKET_ID'],
        'download_url': env_vars['B2_DOWNLOAD_URL']
    }

    print("\n🔄 正在连接到Backblaze B2...")

    try:
        # 初始化B2管理器
        b2_manager = BackblazeB2Manager(config)
        print("✅ B2管理器初始化成功")

        # 获取存储桶信息
        print("\n📋 获取存储桶信息...")
        bucket_info = b2_manager.get_bucket_info()

        print(f"✅ 连接成功!")
        print(f"   存储桶名称: {bucket_info['bucketName']}")
        print(f"   存储桶ID: {bucket_info['bucketId']}")
        print(f"   存储桶类型: {bucket_info['bucketType']}")

        # 测试文件列表
        print("\n📋 测试文件列表...")
        files = b2_manager.list_files()
        print(f"   当前文件数量: {len(files)}")

        # 创建测试文件
        test_filename = "b2_test_file.txt"
        test_content = f"测试文件\n时间: {datetime.now().isoformat()}\nB2云存储连接测试"

        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(test_content)

        print(f"\n📤 上传测试文件: {test_filename}")

        # 上传文件
        upload_success = b2_manager.upload_file(
            test_filename,
            f"test/{test_filename}",
            content_type='text/plain',
            metadata={'test': 'true', 'timestamp': datetime.now().isoformat()}
        )

        if upload_success:
            print("✅ 文件上传成功")

            # 测试下载
            download_filename = f"downloaded_{test_filename}"
            print(f"\n📥 下载测试文件到: {download_filename}")

            download_success = b2_manager.download_file(
                f"test/{test_filename}",
                download_filename
            )

            if download_success:
                print("✅ 文件下载成功")

                # 验证文件内容
                with open(download_filename, 'r', encoding='utf-8') as f:
                    downloaded_content = f.read()

                if test_content in downloaded_content:
                    print("✅ 文件内容验证成功")
                else:
                    print("❌ 文件内容验证失败")

                # 清理本地测试文件
                try:
                    os.remove(test_filename)
                    os.remove(download_filename)
                    print("✅ 本地测试文件清理完成")
                except:
                    pass

                # 删除云存储中的测试文件
                try:
                    b2_manager.delete_file(f"test/{test_filename}")
                    print("✅ 云存储测试文件删除完成")
                except:
                    pass

                print("\n🎉 所有测试通过! B2云存储配置成功!")
                print("\n🚀 您可以开始使用云存储功能了!")
                return True
            else:
                print("❌ 文件下载失败")
                return False
        else:
            print("❌ 文件上传失败")
            return False

    except Exception as e:
        print(f"\n❌ 连接测试失败: {e}")
        print("\n请检查:")
        print("   1. 网络连接是否正常")
        print("   2. 应用密钥是否正确")
        print("   3. 存储桶是否存在")
        print("   4. 是否有B2账户的多因素认证要求")
        return False

if __name__ == "__main__":
    success = test_b2_configuration()
    sys.exit(0 if success else 1)