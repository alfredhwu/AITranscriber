"""音频处理工具 - 格式转换与音频提取"""
import os
import uuid
import subprocess
import shutil
from pydub import AudioSegment

from app.config import UPLOAD_DIR, SUPPORTED_AUDIO_FORMATS, SUPPORTED_VIDEO_FORMATS


def get_ffmpeg_path() -> str:
    """获取ffmpeg路径"""
    path = shutil.which("ffmpeg")
    if path:
        return path
    common_paths = [
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    raise RuntimeError(
        "未找到ffmpeg，请安装ffmpeg。\n"
        "MacOS: brew install ffmpeg\n"
        "Windows: https://ffmpeg.org/download.html"
    )


def extract_audio_from_video(video_path: str) -> str:
    """从视频文件中提取音频"""
    ffmpeg = get_ffmpeg_path()
    output_path = os.path.join(
        UPLOAD_DIR, f"{uuid.uuid4().hex}_extracted.wav"
    )
    cmd = [
        ffmpeg, "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        output_path, "-y"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr}")
    return output_path


def convert_to_wav(input_path: str) -> str:
    """将音频文件转换为16kHz单声道WAV"""
    ext = os.path.splitext(input_path)[1].lower()

    if ext in SUPPORTED_VIDEO_FORMATS:
        return extract_audio_from_video(input_path)

    if ext == ".wav":
        audio = AudioSegment.from_wav(input_path)
    elif ext == ".mp3":
        audio = AudioSegment.from_mp3(input_path)
    elif ext in (".m4a", ".aac"):
        audio = AudioSegment.from_file(input_path, format="m4a" if ext == ".m4a" else "aac")
    elif ext == ".ogg":
        audio = AudioSegment.from_ogg(input_path)
    elif ext == ".flac":
        audio = AudioSegment.from_file(input_path, format="flac")
    else:
        audio = AudioSegment.from_file(input_path)

    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.wav")
    audio.export(output_path, format="wav")
    return output_path


def get_audio_duration(file_path: str) -> float:
    """获取音频时长（秒）"""
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0
    except Exception:
        return 0.0
