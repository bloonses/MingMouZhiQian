@echo off
title Mingmou Attendance - Setup
echo ============================================
echo     Mingmou Attendance - Setup
echo ============================================
echo.

echo [1/4] Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python not found, please install Python 3.8 or later
    pause
    exit /b 1
)
echo [OK] Python environment is ready
echo.

echo [2/4] Installing core dependencies...
python -m pip install --upgrade pip
python -m pip install Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Pillow==10.1.0 openpyxl==3.1.2 qrcode[pil]>=7.4.0
if %errorlevel% neq 0 (
    echo [ERROR] Core dependencies installation failed
    pause
    exit /b 1
)
echo [OK] Core dependencies installed
echo.

echo [3/4] Installing face recognition dependencies...
python -m pip install opencv-python>=4.8.0,<5.0.0 onnxruntime>=1.16.0,<2.0.0 numpy>=1.23.0,<2.0.0 insightface==0.7.3
if %errorlevel% neq 0 (
    echo [WARN] Face recognition dependencies installation failed
    echo Frontend mode will be used instead
    echo Backend InsightFace mode requires manual installation
)
echo [OK] Face recognition dependencies installed
echo.

echo [4/4] Checking model files...
if not exist ".insightface\models\buffalo_l\det_10g.onnx" (
    echo [INFO] Backend InsightFace model not found
    echo To use backend recognition mode, please manually download buffalo_l model
    echo Download: https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
    echo Extract to: .insightface\models\buffalo_l\
    echo.
) else (
    echo [OK] Backend InsightFace model is ready
)
echo.

if not exist "static\models\tiny_face_detector_model-shard1" (
    echo [WARN] Frontend face detection model missing
    echo Please ensure static\models directory contains face-api.js model files
    echo.
) else (
    echo [OK] Frontend model files are complete
)
echo.

echo ============================================
echo     Setup Complete!
echo ============================================
echo.
echo Next step:
echo   Double click "一键启动.bat" to start the system
echo.
echo System supports two recognition modes:
echo   - Frontend mode: browser inference, no extra config
echo   - Backend mode: InsightFace inference, faster and more accurate
echo.
pause
