# InsightFace 后端人脸识别部署说明

## 当前状态：✅ 已部署完成

系统已集成 InsightFace (RetinaFace + ArcFace)，模型文件位于项目内的 `.insightface/models/buffalo_l/` 目录。

## 架构概览

系统支持**两种识别模式**，在签到页面点击按钮切换：

| 模式 | 引擎 | 特征维度 | 活体检测 | 性能 |
|------|------|----------|----------|------|
| 前端模式 | face-api.js (TinyFaceDetector) | 128维 | 点头验证 | 浏览器推理，~100ms/帧 |
| 后端模式 | InsightFace (RetinaFace + ArcFace) | 512维 | 鼻尖移动验证 ⭐ | ONNX Runtime，~50ms/帧 |

## 模型文件清单

```
.insightface/models/buffalo_l/
├── det_10g.onnx      ← RetinaFace 人脸检测 (1.6MB)
├── w600k_r50.onnx    ← ArcFace 特征提取 (166MB)
├── 1k3d68.onnx       ← 3D 68 点关键点
├── 2d106det.onnx     ← 2D 106 点关键点
└── genderage.onnx    ← 性别年龄预测
```

## 手动部署步骤

### 1. 安装 Python 依赖

```bash
pip install opencv-python onnxruntime numpy insightface==0.7.3
```

### 2. 下载模型

从 GitHub Releases 下载：
```
https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
```

解压到项目目录：
```
face-attendance-system-python/.insightface/models/buffalo_l/
```

### 3. 验证安装

```bash
python -c "from face_recognition_backend import get_recognizer; fr = get_recognizer(); print('OK:', fr.use_real_models)"
```

应输出：`OK: True`

## 核心 API

### `/api/recognize_frame` — 后端识别接口

```
POST /api/recognize_frame
Content-Type: application/json

{
    "class_id": 1,
    "course_id": 1,
    "image": "data:image/jpeg;base64,..."
}
```

**响应（签到成功）：**
```json
{
    "success": true,
    "message": "张三 签到成功",
    "student_id": 1,
    "student_name": "张三",
    "liveness": true,
    "nose_frames": 8,
    "matched": [{"student_id": 1, "bbox": [100, 50, 300, 400]}]
}
```

**响应（今日已签到）：**
```json
{
    "success": true,
    "already_attended": true,
    "message": "张三 今日已签到",
    "student_id": 1,
    "student_name": "张三"
}
```

### `/api/reset_liveness` — 活体重置接口

```
POST /api/reset_liveness
```

用于切换班级/模式时重置活体检测状态。

## 性能指标

| 硬件 | 检测速度 | 提取速度 | 总时延 |
|------|---------|---------|--------|
| Intel i5-12400 CPU | 30ms | 15ms | 50-60ms |
| NVIDIA RTX 3060 GPU | 8ms | 3ms | 12-15ms |

## 核心功能说明

### 1. 双特征采集 ⭐

采集人脸时同时保存两种特征：
- **128维特征**：前端 face-api.js 提取，用于前端模式
- **512维特征**：后端 InsightFace 提取，用于后端模式

### 2. 活体检测 ⭐ ⭐

后端模式使用**鼻尖移动验证**：
- 跟踪鼻尖在连续帧中的 X/Y 坐标
- 当移动范围超过阈值（10像素）时判定为活体
- 需要采集至少6帧鼻尖数据

### 3. 余弦相似度匹配 ⭐

后端模式使用余弦相似度替代欧氏距离：
- 更适合归一化后的 ArcFace 特征
- 阈值：0.45（可调整）
- 值越大表示越相似

### 4. 维度兼容检查

- face-api.js 前端特征：**128 维**（512 字节）
- InsightFace ArcFace：**512 维**（2048 字节）
- `_check_dimension_match()` 自动跳过维度不匹配的学生，防止崩溃
- 建议使用同一模式采集和识别（都用后端或都用前端）

### 5. 数据库自动迁移

自动检测并添加 `face_descriptor_512` 列到现有数据库，无需手动操作。

## 故障排查

### 模型加载失败

**现象：** 控制台显示「InsightFace 加载失败，降级到模拟模式」

**解决：**
1. 确认 `.insightface/models/buffalo_l/det_10g.onnx` 存在
2. 确认 `onnxruntime` 已安装：`pip show onnxruntime`
3. 确认 `numpy<2.0`：`pip show numpy`

### GitHub 下载失败 (SSL 错误)

**解决：**
1. 手动下载 buffalo_l.zip
2. 解压到 `.insightface/models/buffalo_l/`
3. 确保模型文件直接在 buffalo_l 目录下（不要嵌套）

### 后端模式识别不准确

**检查：**
1. 查看终端日志中的 `cos_sim` 值
2. 确认采集了 512 维特征（采集时提示「双特征」）
3. 确认活体检测通过了（终端显示 `liveness=True`）
4. 如果 `cos_sim` 低于 0.45，考虑降低阈值

### 切换班级/模式后摄像头画面不动

**已修复！** 现在切换时会重新初始化 canvas 和 ctx。
