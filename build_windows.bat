@echo off
chcp 65001 >nul 2>&1
title AITranscriber - Windows 打包

cd /d "%~dp0"

echo ============================================
echo   AITranscriber Windows 打包
echo ============================================

:: 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: 安装 PyInstaller
pip install -q pyinstaller

:: 清理旧构建
if exist "build\AITranscriber" rmdir /s /q "build\AITranscriber"
if exist "dist\AITranscriber-Windows" rmdir /s /q "dist\AITranscriber-Windows"

echo.
echo [1/3] 使用 PyInstaller 打包...
pyinstaller AITranscriber.spec --noconfirm

echo.
echo [2/3] 组织输出目录...
set DIST_OUT=dist\AITranscriber-Windows
mkdir "%DIST_OUT%"

:: 复制 PyInstaller 输出
xcopy /E /I /Y "dist\AITranscriber\*" "%DIST_OUT%\"

:: 创建数据目录
mkdir "%DIST_OUT%\uploads"
mkdir "%DIST_OUT%\results"
mkdir "%DIST_OUT%\models"
mkdir "%DIST_OUT%\history"

:: 创建启动脚本
(
echo @echo off
echo chcp 65001 ^>nul 2^>^&1
echo title AITranscriber - 语音转录工具
echo cd /d "%%~dp0"
echo echo.
echo echo ==========================================
echo echo   AITranscriber 语音转录工具
echo echo   启动中，请稍候...
echo echo ==========================================
echo echo.
echo where ffmpeg ^>nul 2^>^&1
echo if %%errorlevel%% neq 0 ^(
echo     echo 提示: 未检测到 ffmpeg，部分格式可能不支持
echo     echo 请从 https://ffmpeg.org/download.html 下载并添加到 PATH
echo     echo.
echo ^)
echo AITranscriber.exe
echo pause
) > "%DIST_OUT%\启动AITranscriber.bat"

echo.
echo [3/3] 打包完成!
echo.
echo ============================================
echo   输出目录: dist\AITranscriber-Windows\
echo   双击 "启动AITranscriber.bat" 即可运行
echo ============================================
echo.
pause
