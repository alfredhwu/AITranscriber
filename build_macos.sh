#!/bin/bash
# AITranscriber - macOS 打包脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  AITranscriber macOS 打包"
echo "============================================"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 安装 PyInstaller
pip install -q pyinstaller

# 清理旧构建
rm -rf build/AITranscriber dist/AITranscriber-macOS

echo ""
echo "[1/3] 使用 PyInstaller 打包..."
pyinstaller AITranscriber.spec --noconfirm

echo ""
echo "[2/3] 组织输出目录..."
DIST_OUT="dist/AITranscriber-macOS"
mkdir -p "$DIST_OUT"

# 复制 PyInstaller 输出
cp -R dist/AITranscriber/* "$DIST_OUT/"

# 创建数据目录
mkdir -p "$DIST_OUT/uploads"
mkdir -p "$DIST_OUT/results"
mkdir -p "$DIST_OUT/models"
mkdir -p "$DIST_OUT/history"

# 复制启动脚本
cat > "$DIST_OUT/启动AITranscriber.command" << 'LAUNCHER'
#!/bin/bash
# AITranscriber 启动器
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  AITranscriber 语音转录工具"
echo "  启动中，请稍候..."
echo "=========================================="
echo ""

# 检查 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "提示: 未检测到 ffmpeg，部分格式可能不支持"
    echo "安装方式: brew install ffmpeg"
    echo ""
fi

./AITranscriber
LAUNCHER
chmod +x "$DIST_OUT/启动AITranscriber.command"

echo ""
echo "[3/3] 创建压缩包..."
cd dist
tar -czf AITranscriber-macOS.tar.gz AITranscriber-macOS/
cd ..

echo ""
echo "============================================"
echo "  打包完成!"
echo "  输出目录: dist/AITranscriber-macOS/"
echo "  压缩包:   dist/AITranscriber-macOS.tar.gz"
echo "============================================"
