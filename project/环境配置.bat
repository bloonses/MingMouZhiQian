@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 明眸智签 - 环境配置
echo ============================================
echo     明眸智签 - 环境配置
echo ============================================
echo.

echo [1/4] 检查 Python 环境...
python --version
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)
echo [完成] Python 环境正常
echo.

echo [2/4] 安装核心依赖...
python -m pip install --upgrade pip
python -m pip install "Flask==2.3.3" "Flask-SQLAlchemy==3.0.5" "Pillow==10.1.0" "openpyxl==3.1.2" "qrcode[pil]>=7.4.0"
if %errorlevel% neq 0 (
    echo [错误] 核心依赖安装失败
    pause
    exit /b 1
)
echo [完成] 核心依赖安装完毕
echo.

echo [3/4] 安装人脸识别依赖...
python -m pip install "opencv-python>=4.8.0,<5.0.0" "onnxruntime>=1.16.0,<2.0.0" "numpy>=1.23.0,<2.0.0" "insightface==0.7.3"
if %errorlevel% neq 0 (
    echo [警告] 人脸识别依赖安装失败
    echo         系统将使用浏览器端人脸识别模式
)
echo [完成] 人脸识别依赖检查完毕
echo.

echo [4/4] 检查模型文件...
if not exist ".insightface\models\buffalo_l\det_10g.onnx" (
    echo [提示] 后端 InsightFace 模型未检测到
    echo         如需使用后端识别模式，请手动下载 buffalo_l 模型：
    echo         https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
    echo         解压到 .insightface\models\buffalo_l\ 目录
    echo.
) else (
    echo [完成] 后端 InsightFace 模型已就绪
)
echo.

if not exist "static\models\tiny_face_detector_model-shard1" (
    echo [警告] 前端人脸检测模型文件缺失
    echo         请确保 static\models 目录包含 face-api.js 模型文件
    echo.
) else (
    echo [完成] 前端模型文件完整
)
echo.

echo ============================================
echo     环境配置完成！
echo ============================================
echo.
echo 下一步：
echo   双击 "一键启动.bat" 启动系统
echo.
echo 支持两种识别模式：
echo   - 前端模式：浏览器端推理，无需额外配置
echo   - 后端模式：InsightFace 推理，速度更快精度更高
echo.
pause