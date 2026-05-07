@echo off
chcp 65001 >nul
echo ============================================================
echo STM32 疲劳检测系统 - 串口快速诊断
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
echo ✓ Python 环境正常
echo.

echo [2/3] 检查 pyserial 模块...
python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo ✗ pyserial 未安装
    echo 正在安装...
    pip install pyserial
)
echo ✓ pyserial 已安装
echo.

echo [3/3] 运行串口检查工具...
echo.
python check_serial.py
echo.

echo ============================================================
echo 诊断完成
echo ============================================================
echo.
echo 下一步:
echo   1. 如果找到串口，运行: python test_serial.py
echo   2. 如果没有串口，请连接硬件并安装驱动
echo   3. 查看详细文档: docs\串口连接问题解决方案.md
echo.
pause
