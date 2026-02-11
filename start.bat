@echo off
chcp 65001 >nul 2>&1
title AITranscriber - 语音转录工具

cd /d "%~dp0"

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

python --version

:: 检查虚拟环境
if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
)

echo 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo 检查依赖...
pip install -q -r requirements.txt

:: 检查 ffmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo 警告: 未检测到 ffmpeg
    echo 请从 https://ffmpeg.org/download.html 下载并添加到 PATH
    echo.
)

echo.
echo 启动 AITranscriber...
python run.py
pause
