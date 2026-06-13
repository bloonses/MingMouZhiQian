# 🎯 B2云存储配置流程 - 快速开始

## 第一步：运行配置助手

```bash
python b2_setup_assistant.py
```

这个脚本会：
- ✅ 检查Python依赖
- ✅ 创建环境变量文件 (.env)
- ✅ 生成设置检查清单
- ✅ 创建连接测试脚本
- ✅ 创建集成示例

## 第二步：注册Backblaze B2账号

### 📍 立即访问：https://www.backblaze.com/b2/

### 📋 详细步骤：

1. **注册账号**
   - 📧 输入邮箱地址
   - 🔐 设置密码
   - ✅ 验证邮箱

2. **登录并进入B2 Cloud Storage**
   - 登录后点击 "B2 Cloud Storage"
   - 熟悉界面布局

3. **创建存储桶**
   - 🏷️ 点击 "Create a Bucket"
   - 📝 Bucket Name: `face-attendance-backup`
   - 🔒 Bucket Type: `Private`
   - 💾 **保存显示的Bucket ID**

4. **生成应用密钥**
   - 🔑 点击 "App Keys"
   - ➡️ 点击 "Create Application Key"
   - 📝 Key Name: `face-attendance-app`
   - ✅ 选择B2相关权限
   - 💾 **保存Key ID和Application Key**（只能显示一次！）

## 第三步：配置环境变量

### 📝 编辑 .env 文件

创建或编辑 `.env` 文件，内容如下：

```bash
# Backblaze B2 永久免费环境变量配置
# 1. 访问 https://www.backblaze.com/b2/
# 2. 注册账号并获取访问凭证
# 3. 创建存储桶: face-attendance-backup
# 4. 生成应用密钥

# B2 应用凭证 (请填入您的实际值)
B2_APPLICATION_KEY_ID=您的应用密钥ID
B2_APPLICATION_KEY=您的应用密钥
B2_BUCKET_NAME=face-attendance-backup
B2_BUCKET_ID=您的存储桶ID
B2_DOWNLOAD_URL=https://f004.backblazeb2.com/file

# 应用配置
FLASK_ENV=development
PYTHONPATH=C:\Users\bloon\Downloads\face-attendance-system-python
```

### 🎯 获取凭证位置

```
B2_APPLICATION_KEY_ID = 从App Keys页面获取的Key ID
B2_APPLICATION_KEY = 从App Keys页面获取的Application Key  
B2_BUCKET_ID = 从存储桶页面获取的Bucket ID
```

## 第四步：测试连接

```bash
python test_b2_connection.py
```

如果看到 "所有测试通过!"，说明配置成功！

## 第五步：集成到您的应用

### 📋 修改 app.py 文件

在您的 app.py 中添加以下代码：

```python
from flask import Flask, jsonify, request
from backblaze_b2_storage import BackblazeBackupManager
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 初始化云存储备份
def setup_cloud_backup():
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

# 全局备份管理器
backup_manager = setup_cloud_backup()

# 添加备份API路由
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

@app.route('/backup/student_faces', methods=['POST'])
def backup_student_faces():
    if backup_manager:
        try:
            success = backup_manager.backup_student_faces('static/faces')
            if success:
                return jsonify({'success': True, 'message': '人脸数据备份成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'备份失败: {e}'})
    
    return jsonify({'success': False, 'message': '备份服务不可用'})

@app.route('/cloud/status')
def cloud_status():
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

# 在应用启动时显示配置状态
@app.route('/')
def home():
    config_status = "已配置" if backup_manager else "未配置"
    return f"人脸考勤系统 - B2云存储{config_status}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

## 第六步：测试功能

### 🧪 运行测试

```bash
# 启动应用
python app.py

# 在另一个终端测试API
curl http://localhost:5000/cloud/status
curl -X POST http://localhost:5000/backup/database
```

### 📊 检查结果

- 访问 http://localhost:5000/ 查看配置状态
- 使用API测试备份功能
- 检查B2控制台确认文件上传

## ⚠️ 重要提醒

### 🔐 安全注意事项
- 📧 Key ID和Application Key只能显示一次，请务必保存！
- 🔐 启用B2账号的多因素认证
- 🔄 定期轮换应用密钥
- 💾 重要数据多重备份

### 📞 如果遇到问题
1. 检查环境变量是否正确设置
2. 验证网络连接
3. 确认应用密钥权限
4. 查看B2官方文档

### 💡 成功标志
- ✅ test_b2_connection.py 显示 "所有测试通过!"
- ✅ app.py 启动时显示 "B2云存储已配置"
- ✅ API请求返回成功状态
- ✅ B2控制台可以看到上传的文件

## 🎉 配置完成！

现在您的人脸考勤系统已经具备了完整的永久免费云存储功能！

**成本**: $0永久免费
**存储空间**: 10GB
**使用期限**: 永久
**适合**: 5年的人脸考勤数据存储