# 🎯 如何查找您的Application Key

## 位置：B2控制台 - App Keys页面

### 📍 具体步骤：

1. **登录Backblaze B2控制台**
   - 访问：https://www.backblaze.com/b2/
   - 登录您的账号

2. **进入App Keys页面**
   - 在左侧菜单找到 **"App Keys"**
   - 点击进入

3. **找到您的应用密钥**
   - 您应该能看到刚刚创建的应用密钥
   - Key Name: `face-attendance-app`（或您设置的名称）

4. **复制Application Key**
   - 🔑 **重要提示：Application Key只能显示一次！**
   - 📝 如果您还没有复制，现在立即复制并保存到安全的地方
   - ❌ 如果您关闭了页面，可能需要重新创建新的密钥

### 📋 您需要找到的信息：

```
B2_APPLICATION_KEY=Kxxxxxxx_your_actual_application_key_here
```

### ⚠️ 如果找不到：

1. **重新创建App Key**
   - 进入 App Keys 页面
   - 点击 "Create Application Key"
   - 重新生成一个新的密钥

2. **检查是否有多个密钥**
   - 可能有多个App Keys，找到您为存储桶创建的那个

### 💡 安全提醒：

- 🔒 Application Key是敏感信息，请妥善保管
- 🔄 定期轮换密钥以提高安全性
- 📧 不要将密钥分享给他人

---

## 🔑 需要的信息总结：

请提供：
```
B2_APPLICATION_KEY=您的实际Application Key（从App Keys页面获取）
```

然后我就可以帮您完成完整的配置！