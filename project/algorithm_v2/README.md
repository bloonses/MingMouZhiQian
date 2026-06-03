# 明眸智签 v2.0 - 算法全面升级

## 文件夹结构

```
algorithm_v2/
├── __init__.py                  # 包初始化
├── face_recognition_backend_v2.py  # （待完善）升级后的识别引擎
├── face_quality.py              # 人脸质量评估（已完成）
├── faiss_index.py               # FAISS 向量索引（已完成）
├── liveness_enhanced.py         # 增强活体检测（已完成）
├── face_tracker.py              # 人脸追踪器（已完成）
├── preprocessing.py             # 预处理（光照+姿态）（已完成）
├── requirements.txt             # 依赖（已更新）
└── README.md                    # 本文件
```

## 模块说明

### 1. face_quality.py - 质量评估
- 清晰度（拉普拉斯方差）
- 光照均匀性
- 姿态评分（TODO: 需完善 3D 姿态）
- 加权融合综合分

### 2. faiss_index.py - 向量索引
- IndexFlatIP 内积搜索
- 批量搜索支持
- 持久化/加载

### 3. liveness_enhanced.py - 活体检测
- EAR 眨眼检测
- 鼻尖移动（兼容 v1）
- 多模态分数融合
- (TODO: 活体分类器集成)

### 4. face_tracker.py - 追踪器
- IoU 匹配追踪
- 签到结果缓存
- 轨迹生命周期管理

### 5. preprocessing.py - 预处理
- CLAHE 光照增强
- 自适应伽马校正
- 姿态感知匹配

## 开发进度

- [x] 文件夹结构搭建
- [x] 所有核心模块骨架代码
- [x] requirements.txt 更新
- [ ] 多模板匹配集成进主引擎
- [ ] API 接口扩展
- [ ] 完整端到端测试
- [ ] 性能调优
