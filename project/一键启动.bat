@echo off
chcp 65001 > nul
title 明眸智签 - 人脸识别签到系统

echo ============================================
echo     明眸智签 - 人脸识别签到系统
echo ============================================
echo.

cd /d "%~dp0"

echo [1/4] 检查依赖...
python -m pip install -q Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Pillow==10.1.0 openpyxl==3.1.2 qrcode[pil]>=7.4.0 opencv-python>=4.8.0,<5.0.0 onnxruntime>=1.16.0,<2.0.0 numpy>=1.23.0,<2.0.0 insightface==0.7.3
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败
    echo 系统将使用前端模式运行（功能不受影响）
)
echo [完成] 依赖检查完毕
echo.

echo [2/4] 启动服务器...
echo.
start "明眸智签服务器" cmd /k "python app.py"
echo [完成] 服务器已在后台启动
echo.

echo [3/4] 等待服务器启动...
timeout /t 3 /nobreak > nul
echo [完成] 服务器已就绪
echo.

echo [4/4] 打开浏览器...
start http://127.0.0.1:5000
echo [完成] 浏览器已打开
echo.

echo ============================================
echo     系统已启动！
echo     访问地址: http://127.0.0.1:5000
echo     默认账号: admin / admin123
echo ============================================
echo.
echo 提示：签到页面可切换「前端/后端」识别模式
echo 按任意键退出此窗口（服务器将继续运行）...
pause > nul