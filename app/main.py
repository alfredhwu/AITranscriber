"""FastAPI 主应用"""
import os
import threading
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import (
    UPLOAD_DIR, STATIC_DIR, SUPPORTED_FORMATS, MAX_FILE_SIZE_MB, SYSTEM_INFO
)
from app.audio_utils import convert_to_wav, get_audio_duration
from app.task_manager import task_manager, run_transcription

import app.engines.whisper_engine
import app.engines.funasr_engine
from app.engines.base import get_available_engines

app = FastAPI(title="AITranscriber", version="1.0.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_event():
    """启动时从磁盘加载历史任务"""
    task_manager.load_history()


def _safe_status(status) -> str:
    if hasattr(status, 'value'):
        return str(status.value)
    return str(status)


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/engines")
async def list_engines():
    """获取可用转录引擎列表"""
    engines = get_available_engines()
    return {"engines": engines}


@app.get("/api/system")
async def system_info():
    """系统信息"""
    return {"system": SYSTEM_INFO}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    engine: str = Form("whisper"),
    model: str = Form("base"),
    language: str = Form("auto"),
):
    """上传文件并开始转录"""
    if not file.filename:
        raise HTTPException(400, "未选择文件")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"不支持的文件格式: {ext}。支持: {', '.join(sorted(SUPPORTED_FORMATS))}")

    save_path = os.path.join(UPLOAD_DIR, f"{os.urandom(8).hex()}{ext}")
    try:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(400, f"文件大小 {size_mb:.1f}MB 超过限制 {MAX_FILE_SIZE_MB}MB")

        with open(save_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"文件保存失败: {e}")

    task_id = task_manager.create_task(
        filename=file.filename,
        engine=engine,
        model=model,
        language=language,
        file_path=save_path,
    )

    def process():
        try:
            wav_path = convert_to_wav(save_path)
            run_transcription(task_id, wav_path, engine, model, language)
        except Exception as e:
            task_manager.fail_task(task_id, str(e))

    thread = threading.Thread(target=process, daemon=True)
    thread.start()

    return {"task_id": task_id, "message": "任务已创建"}


@app.post("/api/task/{task_id}/retranscribe")
async def retranscribe_task(
    task_id: str,
    engine: str = Form("whisper"),
    model: str = Form("base"),
    language: str = Form("auto"),
):
    """使用已有媒体文件重新转录"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    # 检查当前是否正在处理
    status_str = _safe_status(task["status"])
    if status_str in ("pending", "processing"):
        raise HTTPException(400, "任务正在处理中，请等待完成后再重新转录")

    media_path = _find_media(task)
    if not media_path:
        raise HTTPException(400, "媒体文件不存在，无法重新转录")

    # 重置任务状态
    if not task_manager.reset_task_for_retranscribe(task_id, engine, model, language):
        raise HTTPException(500, "重置任务失败")

    def process():
        try:
            wav_path = convert_to_wav(media_path)
            run_transcription(task_id, wav_path, engine, model, language)
        except Exception as e:
            task_manager.fail_task(task_id, str(e))

    thread = threading.Thread(target=process, daemon=True)
    thread.start()

    return {"task_id": task_id, "message": "已开始重新转录"}


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    safe_task = {
        "id": task["id"],
        "filename": task["filename"],
        "engine": task["engine"],
        "model": task["model"],
        "language": task["language"],
        "status": _safe_status(task["status"]),
        "progress": task["progress"],
        "message": task["message"],
        "result": task["result"],
        "error": task["error"],
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
    }
    return {"task": safe_task}


@app.get("/api/tasks")
async def list_tasks():
    """获取所有任务（含历史）"""
    tasks = task_manager.get_all_tasks()
    safe_tasks = []
    for task in tasks:
        safe_tasks.append({
            "id": task["id"],
            "filename": task["filename"],
            "engine": task["engine"],
            "model": task["model"],
            "status": _safe_status(task["status"]),
            "progress": task["progress"],
            "message": task["message"],
            "has_result": task.get("result") is not None,
            "has_media": bool(_find_media(task)),
            "created_at": task["created_at"],
            "completed_at": task["completed_at"],
        })
    return {"tasks": safe_tasks}


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务（同时删除媒体文件和转录结果）"""
    if task_manager.delete_task(task_id):
        return {"message": "任务已删除"}
    raise HTTPException(404, "任务不存在")


def _find_media(task: dict) -> str:
    """查找任务关联的原始媒体文件路径"""
    for key in ("media_file", "file_path"):
        fp = task.get(key, "")
        if fp and os.path.isfile(fp):
            return fp
    return ""


def _find_playback_wav(task: dict) -> str:
    """获取播放用的 WAV 文件路径（与转录时间戳一致）。
    如果不存在则从原始媒体实时转换并缓存。"""
    # 已有缓存的 WAV
    wav = task.get("wav_file", "")
    if wav and os.path.isfile(wav):
        return wav

    # 检查任务目录下是否有 audio.wav（历史恢复时可能存在但未加载到内存）
    from app.config import HISTORY_DIR
    wav_in_dir = os.path.join(HISTORY_DIR, task["id"], "audio.wav")
    if os.path.isfile(wav_in_dir):
        return wav_in_dir

    # 从原始媒体转换
    media = _find_media(task)
    if not media:
        return ""

    try:
        wav_path = convert_to_wav(media)
        # 持久化到任务目录
        persisted = task_manager.persist_wav(task["id"], wav_path)
        # 清理临时 WAV
        if os.path.abspath(wav_path) != os.path.abspath(persisted):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        return persisted
    except Exception as e:
        print(f"[播放] WAV 转换失败: {e}")
        return ""


@app.get("/api/audio/{task_id}")
async def get_audio(task_id: str):
    """获取任务的音频文件用于播放（始终返回 WAV 以确保时间线一致）"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    # 优先返回 WAV（与转录时间戳一致）
    wav_path = _find_playback_wav(task)
    if wav_path:
        return FileResponse(
            wav_path,
            media_type="audio/wav",
            filename=os.path.splitext(task["filename"])[0] + ".wav",
        )

    # 回退到原始文件
    file_path = _find_media(task)
    if not file_path:
        raise HTTPException(404, "媒体文件不存在")

    ext = os.path.splitext(file_path)[1].lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac",
        ".wma": "audio/x-ms-wma",
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".flv": "video/x-flv",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=task["filename"],
    )


@app.post("/api/result/{task_id}/edit")
async def edit_segment(task_id: str, segment_index: int = Form(...), text: str = Form(...)):
    """编辑转录结果中的某个片段"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if not task.get("result"):
        raise HTTPException(400, "转录结果不存在")

    with task_manager._lock:
        real_task = task_manager._tasks.get(task_id)
        if real_task and real_task.get("result"):
            segments = real_task["result"].get("segments", [])
            if 0 <= segment_index < len(segments):
                segments[segment_index]["text"] = text
                real_task["result"]["full_text"] = " ".join(s["text"] for s in segments)
                # 编辑后持久化到磁盘
                task_manager._save_result(task_id)
                return {"message": "已更新"}
    raise HTTPException(400, "片段索引无效")


@app.get("/api/export/{task_id}")
async def export_result(task_id: str, format: str = "srt"):
    """导出转录结果"""
    task = task_manager.get_task(task_id)
    if not task or not task.get("result"):
        raise HTTPException(404, "无可导出的结果")

    segments = task["result"].get("segments", [])

    if format == "srt":
        content = _to_srt(segments)
        media_type = "text/srt"
        ext = ".srt"
    elif format == "txt":
        content = task["result"].get("full_text", "")
        media_type = "text/plain"
        ext = ".txt"
    elif format == "json":
        import json
        content = json.dumps(task["result"], ensure_ascii=False, indent=2)
        media_type = "application/json"
        ext = ".json"
    elif format == "vtt":
        content = _to_vtt(segments)
        media_type = "text/vtt"
        ext = ".vtt"
    else:
        raise HTTPException(400, f"不支持的导出格式: {format}")

    filename = os.path.splitext(task["filename"])[0] + ext
    return JSONResponse(
        content={"content": content, "filename": filename},
        media_type="application/json",
    )


def _to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_time_srt(seg["start"])
        end = _format_time_srt(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        speaker = seg.get("speaker", "")
        text = seg["text"]
        if speaker:
            lines.append(f"[{speaker}] {text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _to_vtt(segments) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_time_vtt(seg["start"])
        end = _format_time_vtt(seg["end"])
        lines.append(f"{start} --> {end}")
        speaker = seg.get("speaker", "")
        text = seg["text"]
        if speaker:
            lines.append(f"<v {speaker}>{text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _format_time_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_time_vtt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
