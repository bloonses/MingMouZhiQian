@echo off
chcp 65001 > nul
title 明眸智签 - 人脸识别签到系统

echo ============================================
echo     明眸智签 - 人脸识别签到系统
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] 检查依赖...
python -m pip install -q Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Pillow==10.1.0
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查Python环境
    pause
    exit /b 1
)
echo [完成] 依赖检查完毕
echo.

echo [2/3] 启动服务器...
echo.
python app.py
