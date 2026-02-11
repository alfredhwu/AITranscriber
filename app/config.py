"""应用配置"""
import os
import sys
import platform

HOST = "127.0.0.1"
PORT = 8765

# 判断是否为 PyInstaller 打包环境
if getattr(sys, 'frozen', False):
    # 打包后：可执行文件所在目录作为数据根目录
    BASE_DIR = os.path.dirname(sys.executable)
    # 捆绑的只读资源（static 等）在 _MEIPASS 内
    _BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _BUNDLE_DIR = BASE_DIR
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")
STATIC_DIR = os.path.join(_BUNDLE_DIR, "static")
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "models")
HISTORY_DIR = os.path.join(BASE_DIR, "history")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

SUPPORTED_AUDIO_FORMATS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".wma", ".aac"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}
SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS

MAX_FILE_SIZE_MB = 2000

SYSTEM_INFO = {
    "os": platform.system(),
    "python": sys.version,
    "platform": platform.platform(),
}
