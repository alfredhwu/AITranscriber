#!/bin/bash
# AITranscriber 启动脚本 (MacOS / Linux)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "错误: 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

echo "使用 Python: $($PY --version)"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    $PY -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "检查依赖..."
pip install -q -r requirements.txt

# 检查 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "警告: 未检测到 ffmpeg"
    echo "MacOS 安装: brew install ffmpeg"
    echo "Ubuntu 安装: sudo apt install ffmpeg"
    echo ""
fi

echo ""
echo "启动 AITranscriber..."
python run.py
