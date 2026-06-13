#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速B2连接测试
"""

import os
import sys

def test_quick_connection():
    """快速测试B2连接"""
    print("🚀 快速B2连接测试")
    print("=" * 40)

    # 检查环境变量
    required_vars = ['B2_APPLICATION_KEY_ID', 'B2_APPLICATION_KEY', 'B2_BUCKET_NAME', 'B2_BUCKET_ID']

    print("📋 检查环境变量...")
    for var in required_vars:
        value = os.getenv(var)
        if value and value != 'your_..._here':
            print(f"✅ {var}: 已设置")
        else:
            print(f"❌ {var}: 未设置")
            return False

    print("\n✅ 环境变量检查通过")

    # 测试导入
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from backblaze_b2_storage import BackblazeB2Manager
        print("✅ B2模块导入成功")
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

    # 初始化连接
    config = {
        'application_key_id': os.getenv('B2_APPLICATION_KEY_ID'),
        'application_key': os.getenv('B2_APPLICATION_KEY'),
        'bucket_name': os.getenv('B2_BUCKET_NAME'),
        'bucket_id': os.getenv('B2_BUCKET_ID'),
    }

    try:
        b2_manager = BackblazeB2Manager(config)
        bucket_info = b2_manager.get_bucket_info()
        print(f"\n🎉 连接成功!")
        print(f"   存储桶: {bucket_info['bucketName']}")
        print(f"   类型: {bucket_info['bucketType']}")
        return True
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        return False

if __name__ == "__main__":
    success = test_quick_connection()
    if success:
        print("\n🎯 您的B2云存储已配置成功!")
        print("\n📱 下一步:")
        print("   1. 运行: python app_b2_integration.py")
        print("   2. 访问: http://localhost:5000/cloud/status")
        print("   3. 测试备份功能")
    else:
        print("\n⚠️ 请检查配置后重试")