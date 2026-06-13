# 明眸智签 (MingmouZhiqian)

> 面向大学课堂场景的教师人脸识别考勤系统，让 3-5 分钟的传统点名缩短到 30 秒。

明眸智签是一个基于 Flask + face-api.js / InsightFace 的教室场景考勤系统。支持人脸识别与二维码两种签到方式互为备份，提供大屏实时签到看板、数据统计、Excel 导入导出、多用户多租户隔离等能力，专为投影到教室大屏幕的暗光场景做了视觉与交互优化。

---

## 🏫 最新更新：校园网部署

**2026-06-13 发布！**

明眸智签现已支持**校园网局域网部署与访问**。同一校园网内的任何设备（手机、平板、电脑）只需打开指定链接即可使用系统，无需单独安装。

### 校园网访问特性

| 特性 | 说明 |
|------|------|
| 🌐 局域网访问 | 同一校园网内设备可直接访问 |
| 📱 二维码访问 | 启动后生成访问二维码，手机扫码即用 |
| 🔍 自动 IP 检测 | 自动识别本机所有可用 IP 地址 |
| 🧭 网络诊断 | 启动时自动检测网络状态并输出诊断信息 |
| 📋 访问日志 | 记录所有访问信息以便追踪 |
| ☁️ 云存储集成 | 校园网版内置 B2 云存储备份 |
| 🔐 用户认证 | 保持原有 bcrypt 密码 + 角色权限体系 |

### 三种启动方式

```bash
# 方式 1：校园网版（推荐用于教室场景）
cd project
python start_campus.py       # 一键启动，自动显示 IP 和二维码
# 或
python app_campus.py         # 校园网专用 Flask 应用

# 方式 2：云存储版
python app_with_cloud.py

# 方式 3：标准版
python app.py
```

启动时系统会输出：`🌐 访问地址列表` · `📱 二维码` · `📊 网络诊断`

详细说明参见：
- [project/CAMPUS_NETWORK_GUIDE.md](project/CAMPUS_NETWORK_GUIDE.md)
- [project/CAMPUS_NETWORK_DEPLOYMENT_REPORT.md](project/CAMPUS_NETWORK_DEPLOYMENT_REPORT.md)
- [project/CAMPUS_NETWORK_REQUIREMENT.md](project/CAMPUS_NETWORK_REQUIREMENT.md)

---

## ☁️ 最新更新：云存储集成

**2026-06-13 发布！**

明眸智签现在支持**完整的云端备份与恢复**，确保考勤数据和人脸数据安全存储、永不丢失。

### 支持的云服务商

| 服务商 | 免费额度 | 主要文件 |
|--------|---------|---------|
| **Backblaze B2**（推荐） | 10GB 永久免费 | `backblaze_b2_storage.py` · `b2_setup_assistant.py` |
| **AWS S3** | 5GB · 12个月免费 | `cloud_storage.py` · `cloud_config.py` |
| **Google Cloud Storage** | 5GB · 永久免费 | `cloud_storage.py` · `cloud_config.py` |
| **Azure Blob Storage** | 5GB · 永久免费 | `cloud_storage.py` · `cloud_config.py` |

### 云存储核心能力
- 🔄 **数据库自动备份**：`attendance.db` 定时同步到云端
- 👤 **人脸特征备份**：学生人脸特征向量云端冗余
- ⬇️ **一键恢复**：从云端恢复到任意设备
- 🛠️ **配置辅助脚本**：`setup_cloud_storage.py` · `setup_permanent_cloud.py`
- 🔐 **环境变量管理**：`.env` 文件 + `cloud_config.json` 双配置
- ✅ **安全修复**：密钥泄露防护、CORS 限制、权限校验

快速上手：
```bash
# 1. 一键设置 Backblaze B2
cd project
python b2_setup_assistant.py

# 2. 或启动带云存储的应用
python app_with_cloud.py

# 3. 选择云服务商并填写密钥即可
```

详细文档参见 [project/README_CLOUD.md](project/README_CLOUD.md)

---

## ✨ 最新更新：v2.0 算法全面升级

**2026-06-03 发布！**

| 指标 | 提升幅度 |
|------|---------|
| 识别准确率 | **+44.2%** (42% → 86%) |
| 500人库搜索速度 | **167x** (原 <5ms → 现 0.03ms) |
| 追踪 ID 稳定性 | **100%** |
| 活体检测 | 两模态（鼻尖+眨眼）|

v2.0 核心功能：
- 🚀 **FAISS 向量索引**：毫秒级搜索
- 🎯 **多模板匹配**：质量加权 + KNN 投票
- 👁️ **增强活体**：EAR 眨眼 + 鼻尖移动双检测
- 📈 **质量评估**：清晰度、光照、姿态综合评分
- 🎬 **人脸追踪**：批量推理 + 轨迹管理
- 💡 **光照预处理**：CLAHE + 自适应伽马校正

详细文档参见 [project/algorithm_v2/FINAL_SUMMARY.md](project/algorithm_v2/FINAL_SUMMARY.md)

---

## 目录

- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [功能模块](#功能模块)
- [双模式识别](#双模式识别)
- [活体检测](#活体检测)
- [安全特性](#安全特性)
- [常见问题](#常见问题)
- [文档索引](#文档索引)
- [团队与许可证](#团队与许可证)

---

## 核心特性

- **大屏优先的视觉设计** — 计数器字重 900、字号 48px，深色科技主题适配投影反光环境。
- **双模式人脸识别** — 前端 face-api.js（128 维，点头活体）+ 后端 InsightFace（512 维，鼻尖移动活体），可一键切换。
- **二维码签到备份** — 动态二维码 10 秒自动刷新 + 教师端确认机制，杜绝代签。
- **多租户数据隔离** — 所有业务表携带 `user_id`，普通教师与超级管理员各管各的数据。
- **Excel 导入导出** — 班级、学生、统计数据全部支持 `.xlsx` 批量处理。
- **完整的数据统计** — 近 7 天折线、24 小时分布、签到方式饼图、学生出勤排行。
- **现代灵动有活力的 UI** — 入场过渡、签到成功涟漪、状态边框动态指示，遵循 `prefers-reduced-motion` 无障碍降级。
- **开箱即用** — Windows 下双击 `一键启动.bat` 即可启动；含初始管理员账号。

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端框架 | Flask 2.3 |
| ORM | Flask-SQLAlchemy 3.0 + SQLite |
| 前端识别 | face-api.js（浏览器内 128 维欧氏距离匹配） |
| 后端识别 v1 | InsightFace 0.7.3（buffalo_l 模型，512 维余弦相似度） |
| 后端识别 v2 | InsightFace + FAISS + 多模板匹配（准确率 +44.2%） |
| 向量索引 | FAISS (IndexFlatIP) |
| 推理引擎 | ONNX Runtime |
| 图像处理 | OpenCV、Pillow、NumPy |
| 二维码 | qrcode |
| 表格处理 | openpyxl |
| 云存储 | Backblaze B2（10GB永久免费）· AWS S3 · GCP Storage · Azure Blob |
| 配置管理 | `.env` + `cloud_config.json` 双方案 |
| 集成入口 | `app_with_cloud.py`（完整云存储版）· `cloud_integration.py`（路由层） |
| 前端模板 | Jinja2 + 原生 HTML/CSS/JS（无构建步骤） |

详细依赖见：
- v1: [project/requirements.txt](project/requirements.txt)
- v2: [project/algorithm_v2/requirements.txt](project/algorithm_v2/requirements.txt)

---

## 项目结构

```
.
├── README.md                        # 本文件
└── project/                         # 主项目目录
    ├── app.py                       # Flask 主应用（路由、模型、API）
    ├── face_recognition_backend.py  # InsightFace 后端识别封装 (v1)
    ├── requirements.txt             # Python 依赖 (v1)
    ├── start.bat                    # 启动脚本
    ├── 一键启动.bat                  # 一键启动（中文环境）
    ├── 环境配置.bat                  # 依赖安装脚本
    ├── copy_and_verify_models.py    # 模型文件校验
    ├── download_model_manually.py   # 模型下载工具
    ├── download_models.py           # 模型批量下载
    ├── fix_model_nesting.py         # 模型目录修复
    ├── PRODUCT.md                   # 产品定位与设计原则
    ├── 使用说明.md                   # 终端用户手册
    ├── 快速入门指南.md               # 上手指南
    ├── 关键参数文档.md               # 识别参数调优
    ├── 开发任务清单.md               # 团队开发进度
    ├── 五人小组学习计划.md           # 团队学习计划
    ├── 项目代码解读.md               # 代码详解
    ├── INSIGHTFACE_DEPLOYMENT.md    # InsightFace 部署说明
    │
    ├── algorithm_v2/                # ✨ 全新算法 v2.0
    │   ├── face_recognition_backend_v2.py  # v2 识别引擎
    │   ├── api_v2.py                # v2 API 接口
    │   ├── db_migration.py          # 数据库迁移（多模板）
    │   ├── face_quality.py          # 人脸质量评估
    │   ├── faiss_index.py           # FAISS 向量索引
    │   ├── liveness_enhanced.py     # 增强活体检测（眨眼+鼻尖）
    │   ├── face_tracker.py          # 人脸追踪器
    │   ├── multi_template_matcher.py # 多模板匹配系统
    │   ├── optimized_inference.py   # 优化推理
    │   ├── preprocessing.py         # 光照+姿态预处理
    │   ├── requirements.txt         # v2 依赖（含 faiss-cpu）
    │   ├── test_*.py                # 单元测试（48个用例，100%通过）
    │   ├── README.md                # v2 模块文档
    │   ├── FINAL_SUMMARY.md         # v2 最终总结
    │   └── FINAL_SUMMARY_COMPLETE.md
    │
    ├── ☁️ 云存储核心文件（新增）
    ├── .env                         # 环境变量配置（B2密钥等）
    ├── app_with_cloud.py           # 集成云存储的主应用入口
    ├── backblaze_b2_storage.py     # Backblaze B2 管理器（推荐）
    ├── b2_setup_assistant.py       # B2 一键设置助手
    ├── app_b2_integration.py       # B2 与主应用集成
    ├── cloud_storage.py             # 通用云存储管理器（S3/GCP/Azure）
    ├── cloud_integration.py         # Flask 路由层 + 自动备份
    ├── cloud_config.py              # 多服务商配置管理
    ├── setup_cloud_storage.py      # 云存储自动设置脚本
    ├── setup_permanent_cloud.py    # 永久免费云方案设置
    ├── permanent_free_storage.py   # 永久免费存储策略
    ├── demo_cloud_storage.py       # 云存储演示脚本
    ├── test_b2_connection.py       # B2 连接测试
    ├── test_quick_b2.py            # B2 快速测试
    │
    ├── 🏫 校园网部署核心文件（新增）
    ├── app_campus.py              # 校园网专用 Flask 主应用（含云存储 + 局域网访问）
    ├── start_campus.py          # 校园网一键启动脚本（自动检测IP + 生成二维码）
    ├── campus_index.html        # 校园网主页 HTML
    │
    ├── 🌐 独立静态页面（项目根目录）
    ├── base.html                # 独立页面布局（非 templates/）
    ├── index.html               # 独立静态主页（含云存储状态卡片 + 校园网访问信息）
    │
    ├── 📄 云存储相关文档
    ├── README_CLOUD.md             # 云存储功能完整说明
    ├── CLOUD_PROVIDER_CHOICE_GUIDE.md # 云服务商选择指南
    ├── B2_QUICK_SETUP_GUIDE.md     # B2 快速设置指南
    ├── PERMANENT_CLOUD_GUIDE.md    # 永久免费云配置指南
    ├── CROSS_COMPUTER_DEPLOYMENT.md # 跨电脑部署指南
    ├── HOW_TO_FIND_APP_KEY.md      # 如何获取应用密钥
    ├── CLOUD_INTEGRATION_REPORT.md  # 云集成测试报告
    ├── SECURITY_FIXES.md           # 安全修复记录
    │
    ├── 📄 校园网相关文档
    ├── CAMPUS_NETWORK_GUIDE.md    # 校园网访问部署指南
    ├── CAMPUS_NETWORK_DEPLOYMENT_REPORT.md # 校园网部署报告
    ├── CAMPUS_NETWORK_REQUIREMENT.md # 校园网要求清单
    ├── PAGE_INTEGRATION_REPORT.md   # 独立页面集成报告（HTML 样式说明）
    │
    ├── instance/
    │   └── attendance.db            # SQLite 数据库（运行后生成）
    ├── static/
    │   ├── face-api.js/             # 前端识别库与模型
    │   └── models/                  # face-api.js 的人脸检测/识别模型
    └── templates/                   # Jinja2 模板
        ├── base.html                # 全局布局
        ├── index.html               # 仪表盘
        ├── login.html               # 登录
        ├── register.html            # 注册
        ├── forgot_password.html     # 找回密码
        ├── super_admin.html         # 超级管理员（全面重构）
        ├── courses.html             # 课程列表
        ├── add_course.html / edit_course.html
        ├── classes.html             # 班级列表
        ├── add_class.html / edit_class.html
        ├── assign_classes.html      # 课程分配班级
        ├── students.html            # 学生列表
        ├── add_student.html / edit_student.html
        ├── capture_face.html        # 人脸采集
        ├── attendance.html          # 人脸识别签到（单人）
        ├── batch_attendance.html    # 批量签到（多人）
        ├── qrcode_attendance.html   # 二维码签到（教师端）
        ├── qr_signin.html           # 二维码签到（学生端）
        ├── qr_signin_error.html
        ├── records.html             # 签到记录
        ├── statistics.html          # 数据统计
        ├── test_face_detection.html
        └── simple_test.html
```

---

## 快速开始

### 环境要求

- 操作系统：Windows 10/11（macOS / Linux 亦可，手动启动即可）
- Python：3.8+
- 浏览器：Chrome、Edge、Firefox（需授予摄像头权限）
- 摄像头：任意可被浏览器识别的 USB / 内置摄像头

### 一键启动（Windows）

1. 双击 `project/环境配置.bat` 安装 Python 依赖（含 InsightFace 引擎）
2. 双击 `project/一键启动.bat` 启动系统
3. 浏览器打开 <http://localhost:5000>

### 手动启动

```bash
cd project
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

### 初始账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 超级管理员 | `admin` | `admin123` |

> ⚠️ 生产环境部署前请立即修改默认密码，并通过环境变量 `SECRET_KEY` 覆盖 Flask 会话密钥。

### 摄像头访问

- 首次访问需要授予浏览器摄像头权限
- 必须使用 `http://localhost:5000` 或 `http://127.0.0.1:5000` 访问（localhost 在浏览器中被视为安全来源）
- 如拒绝授权，请点击地址栏左侧 🔒 图标重新开启

---

## 功能模块

### 1. 仪表盘
- 今日签到总数、班级数、学生数
- 各班级出勤率与已签/应到实时统计
- 大屏投影优化（深色背景 + 高对比度数字）

### 2. 班级与学生管理
- 班级 / 学生的增删改查
- Excel 批量导入与导出
- 学生人脸采集（同时采集 128 维和 512 维双特征）

### 3. 课程管理
- 课程增删改查
- 一门课程可关联多个班级
- 删除课程时自动清理关联的签到记录

### 4. 人脸识别签到
- **单人模式** — 选择班级 / 课程，自动启动摄像头，活体通过后逐人识别签到
- **批量模式** — 同时检测多名学生，识别后自动签到
- 手动签到兜底（点击学生旁 📝 按钮）
- 清除当日签到数据

### 5. 二维码签到（备用方案）
- 教师端生成动态二维码，**每 10 秒自动刷新**
- 学生扫码后输入学号，提交签到请求
- 教师在待确认列表中手动确认 / 拒绝
- 同一学生同一天只能签到一次（人脸 / 二维码互斥）

### 6. 签到记录与统计
- 按班级、日期筛选签到历史
- 近 7 天每日签到折线
- 24 小时签到时间分布
- 签到方式饼图
- 学生出勤排行榜
- 导出多 Sheet 统计 Excel

### 7. 超级管理员
- 管理所有用户（增删改、重置密码）
- 全局数据看板
- 跨租户的学生信息管理

### 8. 账户安全
- 登录、注册、找回密码（安全问题 + 安全答案）
- bcrypt 密码哈希
- 每次登录清除旧会话

### 9. 云存储与跨设备同步（新增）
- **Backblaze B2**：10GB 永久免费，推荐作为首选
- **AWS S3 / GCP / Azure**：多家云服务商一键切换
- **数据库自动备份**：考勤数据、用户信息、签到记录
- **人脸特征云端冗余**：防止本地磁盘故障
- **一键恢复**：从云端恢复到任意设备，实现多电脑同步
- **配置脚本**：`b2_setup_assistant.py` · `setup_cloud_storage.py`
- **安全加固**：密钥仅存于 `.env` 文件、HTTPS 传输、CORS 限制

### 10. 校园网局域网部署（新增）
- **`app_campus.py`**：校园网专用 Flask 应用，内置云存储 + 局域网访问
- **`start_campus.py`**：一键启动脚本，自动检测 IP、生成访问二维码、输出网络诊断
- **多设备访问**：同一校园网内任何电脑 / 手机 / 平板可直接访问
- **访问日志**：记录所有访问信息
- **安全不变**：保持原有的 bcrypt 密码 + 角色权限体系
- **独立静态页面**：`base.html` / `index.html`（项目根目录） — 与 Jinja2 模板分离，适用于直接打开的 HTML 访问方式

---

## 双模式识别 + 全新 v2.0

### v1 双模式识别

| 维度 | 前端模式 | 后端模式 |
|------|----------|----------|
| 技术栈 | face-api.js | InsightFace（Python） |
| 特征维度 | 128 维 | 512 维 |
| 匹配算法 | 欧氏距离（阈值 0.6） | 余弦相似度（阈值 0.45） |
| 活体方式 | 点头检测 | 鼻尖移动检测 |
| 推理位置 | 浏览器 | 后端 ONNX Runtime |
| 单帧速度 | 中等 | ~50ms / 帧 |
| 多人检测 | 支持 | 支持 |
| LFW 准确率 | 高 | 99.8% |
| 启用方式 | 默认 | 安装 InsightFace 后自动启用 |

在签到页面点击 **「模式: 前端 / 后端」** 即可切换。

---

### v2.0 算法升级（推荐使用）

v2 在 v1 的基础上全面升级：

- **识别准确率 +44.2%**（42% → 86%）
- **167x 搜索提速**（<5ms → 0.03ms for 500人）
- 多模板匹配 + 质量加权 + KNN 投票
- FAISS 向量索引
- 增强活体检测（眨眼 + 鼻尖）
- 批量推理 + 人脸追踪

使用：
```python
from algorithm_v2.face_recognition_backend_v2 import get_recognizer_v2
recognizer = get_recognizer_v2()  # API 与 v1 完全兼容！
```

---

## 活体检测

为防止使用照片 / 视频进行作弊签到，系统在两种识别模式下均内置活体检测：

- **前端模式** — 跟踪鼻尖 Y 轴位移，要求用户完成一次自然点头
- **后端模式** — 跟踪鼻尖在连续帧中的移动距离，真人会自然微动头部，照片无此特征

> 详细参数与调优方式见 [project/关键参数文档.md](project/关键参数文档.md)。

---

## 安全特性

| 措施 | 说明 |
|------|------|
| bcrypt 密码哈希 | 用户密码不以明文存储 |
| 会话安全 | 登录时清除旧会话，防会话固定 |
| 数据隔离 | 所有业务表带 `user_id`，多租户严格隔离 |
| CSRF 防护 | 删除 / 清除等写操作使用 POST 方法 |
| 输入验证 | 注册、添加等操作校验空值与长度 |
| 二维码防代签 | 10 秒自动刷新 + 教师确认 |
| 文件上传限制 | 单次最大 16 MB |
| 错误信息保护 | API 错误响应不暴露内部细节 |

---

## 常见问题

**摄像头无法打开？**
检查浏览器授权、是否被其他程序占用，并确认使用 `localhost` 访问。

**人脸识别不准确？**
确保每位学生都已采集人脸，采集和识别使用同一模式；可参考参数文档调整阈值。

**后端模式提示"请轻微移动头部"？**
属于活体检测正常流程，请在画面中自然轻微移动头部，收集 6 帧鼻尖数据后会自动判断。

**如何清除当日签到数据？**
在签到页面点击「🗑️ 清除签到」。

**手机扫码后无法打开？**
确保手机和电脑在同一局域网，二维码链接会自动使用当前服务器 IP。

**如何调整识别阈值？**
详见 [project/关键参数文档.md](project/关键参数文档.md)。

---

## 文档索引

| 文档 | 用途 |
|------|------|
| [project/PRODUCT.md](project/PRODUCT.md) | 产品定位、目标用户、设计原则 |
| [project/使用说明.md](project/使用说明.md) | 完整终端用户手册 |
| [project/快速入门指南.md](project/快速入门指南.md) | 上手教程 |
| [project/关键参数文档.md](project/关键参数文档.md) | 识别参数调优指南 |
| [project/项目代码解读.md](project/项目代码解读.md) | 代码详解 |
| [project/INSIGHTFACE_DEPLOYMENT.md](project/INSIGHTFACE_DEPLOYMENT.md) | InsightFace 部署说明 |
| [project/开发任务清单.md](project/开发任务清单.md) | 团队开发进度追踪 |
| [project/五人小组学习计划.md](project/五人小组学习计划.md) | 团队学习计划 |
| | |
| **✨ v2.0 文档** | |
| [project/algorithm_v2/README.md](project/algorithm_v2/README.md) | v2 模块说明 |
| [project/algorithm_v2/FINAL_SUMMARY.md](project/algorithm_v2/FINAL_SUMMARY.md) | v2 最终总结 |
| [project/algorithm_v2/FINAL_SUMMARY_COMPLETE.md](project/algorithm_v2/FINAL_SUMMARY_COMPLETE.md) | v2 详细报告 |
| | |
| **☁️ 云存储文档** | |
| [project/README_CLOUD.md](project/README_CLOUD.md) | 云存储功能完整说明 |
| [project/CLOUD_PROVIDER_CHOICE_GUIDE.md](project/CLOUD_PROVIDER_CHOICE_GUIDE.md) | 云服务商选择指南 |
| [project/B2_QUICK_SETUP_GUIDE.md](project/B2_QUICK_SETUP_GUIDE.md) | B2 快速设置指南 |
| [project/PERMANENT_CLOUD_GUIDE.md](project/PERMANENT_CLOUD_GUIDE.md) | 永久免费云方案 |
| [project/CROSS_COMPUTER_DEPLOYMENT.md](project/CROSS_COMPUTER_DEPLOYMENT.md) | 跨电脑部署指南 |
| [project/HOW_TO_FIND_APP_KEY.md](project/HOW_TO_FIND_APP_KEY.md) | 如何获取 B2 应用密钥 |
| [project/CLOUD_INTEGRATION_REPORT.md](project/CLOUD_INTEGRATION_REPORT.md) | 云集成测试报告 |
| [project/SECURITY_FIXES.md](project/SECURITY_FIXES.md) | 安全修复记录 |
| | |
| **🏫 校园网文档** | |
| [project/CAMPUS_NETWORK_GUIDE.md](project/CAMPUS_NETWORK_GUIDE.md) | 校园网访问部署指南 |
| [project/CAMPUS_NETWORK_DEPLOYMENT_REPORT.md](project/CAMPUS_NETWORK_DEPLOYMENT_REPORT.md) | 校园网部署报告 |
| [project/CAMPUS_NETWORK_REQUIREMENT.md](project/CAMPUS_NETWORK_REQUIREMENT.md) | 校园网要求清单 |
| [project/PAGE_INTEGRATION_REPORT.md](project/PAGE_INTEGRATION_REPORT.md) | 独立页面集成报告 |

---

## 团队与许可证

本项目由五人小组协作开发，定位为大学课堂场景的轻量级考勤工具。

仓库地址：<https://github.com/bloonses/MingMouZhiQian>
