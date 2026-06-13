# 🚀 跨电脑部署指南 - B2云存储配置

## 📋 部署前准备

### 🎯 需要重新配置的信息：

#### 1. 环境变量（必须配置）
```bash
# 在新电脑上创建 .env 文件
# 复制以下内容并填入您的B2凭证
```

#### 2. Python环境（必须安装）
```bash
# 安装必要的Python包
pip install boto3 python-dotenv requests flask
```

#### 3. 项目文件（需要复制）
- 所有Python文件
- 数据库文件（attendance.db）
- 人脸数据目录（static/faces）

---

## 🔧 详细部署步骤

### 第1步：在新电脑上设置环境

#### 1.1 安装Python依赖
```bash
pip install boto3 python-dotenv requests flask
```

#### 1.2 创建环境变量文件
在新电脑上创建 `.env` 文件：

```bash
# .env 文件内容
B2_APPLICATION_KEY_ID=0028a0b471a3e200000000000
B2_APPLICATION_KEY=K006CQMW/zbesozKYC+aWj88KYAToHs
B2_BUCKET_NAME=face-attendance-backup
B2_BUCKET_ID=0b8456257702c41c9ae30b12
B2_DOWNLOAD_URL=https://f004.backblazeb2.com/file

FLASK_ENV=development
PYTHONPATH=项目路径
```

### 第2步：复制项目文件

#### 2.1 必须复制的文件
```
face-attendance-system/
├── app_b2_integration.py      # 主要应用文件
├── backblaze_b2_storage.py   # B2存储模块
├── .env                      # 环境变量
├── test_quick_b2.py         # 测试脚本
├── attendance.db           # 数据库文件（如果存在）
└── static/faces/           # 人脸数据目录（如果存在）
```

#### 2.2 可选文件
```
├── app.py                   # 原始应用文件
├── cloud_storage.py         # 通用云存储模块
├── README_CLOUD.md          # 云存储文档
└── B2_QUICK_SETUP_GUIDE.md  # 设置指南
```

### 第3步：测试配置

#### 3.1 测试B2连接
```bash
python test_quick_b2.py
```

#### 3.2 启动应用
```bash
python app_b2_integration.py
```

#### 3.3 验证功能
```bash
# 检查状态
curl http://localhost:5000/cloud/status

# 测试备份
curl -X POST http://localhost:5000/backup/database
```

---

## 📱 部署到服务器（可选）

如果您想部署到云服务器，可以使用以下配置：

### Docker部署（推荐）

#### 3.1 创建 Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY . .

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app_b2_integration.py"]
```

#### 3.2 创建 requirements.txt
```
flask==2.3.3
boto3==1.28.57
python-dotenv==1.0.0
requests==2.31.0
```

#### 3.3 运行Docker容器
```bash
docker build -t face-attendance-b2 .
docker run -p 5000:5000 --env-file .env face-attendance-b2
```

### 传统服务器部署

#### 3.1 使用Gunicorn
```bash
# 安装Gunicorn
pip install gunicorn

# 启动应用
gunicorn --bind 0.0.0.0:5000 app_b2_integration:app
```

#### 3.2 使用PM2（Node.js进程管理器）
```bash
# 安装PM2
npm install -g pm2

# 创建PM2配置文件
echo 'module.exports = {
  apps: [{
    name: "face-attendance",
    script: "app_b2_integration.py",
    instances: 1,
    exec_mode: "fork",
    env: {
      NODE_ENV: "production",
      B2_APPLICATION_KEY_ID: "0028a0b471a3e200000000000",
      B2_APPLICATION_KEY: "K006CQMW/zbesozKYC+aWj88KYAToHs",
      B2_BUCKET_NAME: "face-attendance-backup",
      B2_BUCKET_ID: "0b8456257702c41c9ae30b12",
      B2_DOWNLOAD_URL: "https://f004.backblazeb2.com/file"
    }
  }]
}' > ecosystem.config.js

# 启动应用
pm2 start ecosystem.config.js
```

---

## 🔒 安全注意事项

### 1. 环境变量安全
- 🔒 不要将 `.env` 文件提交到版本控制
- 🔒 使用 `.gitignore` 排除敏感文件
- 🔒 定期轮换B2应用密钥

### 2. 网络安全
- 🔒 启用HTTPS（建议使用Nginx反向代理）
- 🔒 配置防火墙规则
- 🔒 限制访问IP地址

### 3. 数据安全
- 🔒 定期备份数据库
- 🔒 加密敏感数据
- 🔒 监控异常访问

---

## 📞 部署故障排除

### 常见问题

#### 1. 连接失败
```bash
# 检查环境变量
python test_quick_b2.py

# 检查网络连接
curl -I https://f004.backblazeb2.com/file
```

#### 2. 模块导入失败
```bash
# 检查Python路径
export PYTHONPATH=/path/to/your/project

# 重新安装依赖
pip install -r requirements.txt
```

#### 3. 权限错误
```bash
# 检查B2应用密钥权限
# 确保密钥有读写权限
```

### 日志查看
```bash
# 查看应用日志
python app_b2_integration.py 2>&1 | tee app.log

# 查看系统日志
journalctl -u your-app-name
```

---

## 🎯 部署检查清单

### 部署前确认：
- [ ] 安装Python 3.8+
- [ ] 安装必要依赖包
- [ ] 创建环境变量文件
- [ ] 复制项目文件
- [ ] 测试B2连接
- [ ] 验证数据库文件

### 部署后确认：
- [ ] 应用正常启动
- [ ] 云存储连接正常
- [ ] 备份功能正常
- [ ] API接口响应正常
- [ ] 日志记录正常

---

## 📞 技术支持

如果您在部署过程中遇到问题：

1. **首先运行测试脚本**：
   ```bash
   python test_quick_b2.py
   ```

2. **检查环境变量**：
   ```bash
   echo $B2_APPLICATION_KEY_ID
   echo $B2_APPLICATION_KEY
   ```

3. **查看详细错误**：
   ```bash
   python app_b2_integration.py
   ```

4. **查看日志**：
   ```bash
   tail -f app.log
   ```

---

## 🎉 总结

跨电脑部署只需要：
1. **安装Python依赖**（5分钟）
2. **创建环境变量文件**（1分钟）
  
其他文件都可以直接复制使用！

**您的B2云存储配置在所有电脑上都是相同的**，因为使用的是同一个存储桶。