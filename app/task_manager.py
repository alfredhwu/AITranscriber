"""任务管理器 - 管理转录任务的生命周期，支持磁盘持久化"""
import os
import json
import glob
import uuid
import time
import shutil
import threading
import traceback
from typing import Dict, Any, Optional, List
from enum import Enum

from app.config import UPLOAD_DIR, RESULT_DIR, HISTORY_DIR


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _status_str(status) -> str:
    """将 TaskStatus 转为纯字符串"""
    if hasattr(status, "value"):
        return str(status.value)
    return str(status)


class TaskManager:
    """转录任务管理器（带磁盘持久化）"""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------------
    # 持久化：每个任务在 HISTORY_DIR/{task_id}/ 下保存
    #   - meta.json   : 任务元数据（不含 result）
    #   - result.json  : 转录结果
    #   - 原始音视频文件（拷贝或移动到该目录）
    # ----------------------------------------------------------------

    def _task_dir(self, task_id: str) -> str:
        return os.path.join(HISTORY_DIR, task_id)

    def _save_meta(self, task_id: str):
        """保存任务元数据到磁盘"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task_dir = self._task_dir(task_id)
        os.makedirs(task_dir, exist_ok=True)

        meta = {
            "id": task["id"],
            "filename": task["filename"],
            "engine": task["engine"],
            "model": task["model"],
            "language": task["language"],
            "media_file": task.get("media_file", ""),
            "status": _status_str(task["status"]),
            "progress": task["progress"],
            "message": task["message"],
            "error": task["error"],
            "created_at": task["created_at"],
            "completed_at": task["completed_at"],
        }
        meta_path = os.path.join(task_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _save_result(self, task_id: str):
        """保存转录结果到磁盘"""
        task = self._tasks.get(task_id)
        if not task or not task.get("result"):
            return
        task_dir = self._task_dir(task_id)
        os.makedirs(task_dir, exist_ok=True)

        result_path = os.path.join(task_dir, "result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(task["result"], f, ensure_ascii=False, indent=2)

        # 同时保存到旧的 results/ 目录（兼容导出等功能）
        compat_path = os.path.join(RESULT_DIR, f"{task_id}.json")
        with open(compat_path, "w", encoding="utf-8") as f:
            json.dump(task["result"], f, ensure_ascii=False, indent=2)

    def _persist_media(self, task_id: str, src_path: str) -> str:
        """将上传的原始媒体文件持久化到任务目录，返回新路径"""
        task_dir = self._task_dir(task_id)
        os.makedirs(task_dir, exist_ok=True)

        ext = os.path.splitext(src_path)[1]
        dest_path = os.path.join(task_dir, f"media{ext}")

        if os.path.abspath(src_path) != os.path.abspath(dest_path):
            shutil.copy2(src_path, dest_path)
        return dest_path

    def persist_wav(self, task_id: str, wav_path: str) -> str:
        """将转录用的 WAV 文件持久化到任务目录，供播放使用（确保时间线一致）"""
        task_dir = self._task_dir(task_id)
        os.makedirs(task_dir, exist_ok=True)

        dest_path = os.path.join(task_dir, "audio.wav")
        if os.path.abspath(wav_path) != os.path.abspath(dest_path):
            shutil.copy2(wav_path, dest_path)

        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["wav_file"] = dest_path
        return dest_path

    def load_history(self):
        """从磁盘加载所有历史任务"""
        if not os.path.isdir(HISTORY_DIR):
            return

        loaded = 0
        for entry in sorted(os.listdir(HISTORY_DIR)):
            task_dir = os.path.join(HISTORY_DIR, entry)
            if not os.path.isdir(task_dir):
                continue

            meta_path = os.path.join(task_dir, "meta.json")
            if not os.path.isfile(meta_path):
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                task_id = meta["id"]

                # 恢复媒体文件路径
                media_file = meta.get("media_file", "")
                file_path = ""
                if media_file and os.path.isfile(media_file):
                    file_path = media_file
                else:
                    # 尝试查找 task_dir 下的 media.* 文件
                    media_files = glob.glob(os.path.join(task_dir, "media.*"))
                    if media_files:
                        file_path = media_files[0]

                # 恢复 WAV 播放文件路径
                wav_file = ""
                wav_path_candidate = os.path.join(task_dir, "audio.wav")
                if os.path.isfile(wav_path_candidate):
                    wav_file = wav_path_candidate

                # 加载转录结果
                result = None
                result_path = os.path.join(task_dir, "result.json")
                if os.path.isfile(result_path):
                    with open(result_path, "r", encoding="utf-8") as f:
                        result = json.load(f)

                # 构建任务对象
                status_str = meta.get("status", "completed")
                # 未完成的历史任务标记为失败（因为进程已重启）
                if status_str in ("pending", "processing"):
                    if result:
                        status_str = "completed"
                    else:
                        status_str = "failed"

                task = {
                    "id": task_id,
                    "filename": meta.get("filename", "unknown"),
                    "engine": meta.get("engine", ""),
                    "model": meta.get("model", ""),
                    "language": meta.get("language", ""),
                    "file_path": file_path,
                    "media_file": file_path,
                    "wav_file": wav_file,
                    "status": status_str,
                    "progress": 1.0 if status_str == "completed" else 0.0,
                    "message": meta.get("message", "从历史记录恢复"),
                    "result": result,
                    "error": meta.get("error"),
                    "created_at": meta.get("created_at", 0),
                    "completed_at": meta.get("completed_at"),
                }

                with self._lock:
                    self._tasks[task_id] = task
                loaded += 1

            except Exception as e:
                print(f"[历史加载] 跳过 {entry}: {e}")

        if loaded > 0:
            print(f"[历史加载] 已恢复 {loaded} 条历史任务")

    # ----------------------------------------------------------------
    # CRUD 操作
    # ----------------------------------------------------------------

    def create_task(self, filename: str, engine: str, model: str,
                    language: str, file_path: str) -> str:
        task_id = uuid.uuid4().hex[:12]

        task = {
            "id": task_id,
            "filename": filename,
            "engine": engine,
            "model": model,
            "language": language,
            "file_path": file_path,
            "media_file": "",
            "status": TaskStatus.PENDING,
            "progress": 0.0,
            "message": "等待处理...",
            "result": None,
            "error": None,
            "created_at": time.time(),
            "completed_at": None,
        }

        # 持久化原始媒体文件
        media_path = self._persist_media(task_id, file_path)
        task["media_file"] = media_path

        with self._lock:
            self._tasks[task_id] = task
            self._save_meta(task_id)

        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                return task.copy()
            return None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            # 按创建时间倒序返回
            tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.get("created_at", 0),
                reverse=True,
            )
            return [t.copy() for t in tasks]

    def update_progress(self, task_id: str, progress: float, message: str = ""):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["progress"] = progress
                if message:
                    self._tasks[task_id]["message"] = message

    def reset_task_for_retranscribe(self, task_id: str, engine: str, model: str, language: str) -> bool:
        """重置任务状态以便重新转录，返回是否成功"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task["engine"] = engine
            task["model"] = model
            task["language"] = language
            task["status"] = TaskStatus.PENDING
            task["progress"] = 0.0
            task["message"] = "等待重新转录..."
            task["result"] = None
            task["error"] = None
            task["completed_at"] = None
            self._save_meta(task_id)
            # 删除旧的 result.json
            result_path = os.path.join(self._task_dir(task_id), "result.json")
            if os.path.isfile(result_path):
                try:
                    os.remove(result_path)
                except OSError:
                    pass
            return True

    def complete_task(self, task_id: str, result: Dict):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = TaskStatus.COMPLETED
                self._tasks[task_id]["progress"] = 1.0
                self._tasks[task_id]["message"] = "转录完成"
                self._tasks[task_id]["result"] = result
                self._tasks[task_id]["completed_at"] = time.time()

                self._save_result(task_id)
                self._save_meta(task_id)

    def fail_task(self, task_id: str, error: str):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = TaskStatus.FAILED
                self._tasks[task_id]["message"] = f"失败: {error}"
                self._tasks[task_id]["error"] = error

                self._save_meta(task_id)

    def save_edited_result(self, task_id: str):
        """编辑片段后，将修改后的 result 持久化到磁盘"""
        with self._lock:
            if task_id in self._tasks and self._tasks[task_id].get("result"):
                self._save_result(task_id)

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]

                # 删除上传目录中的临时文件
                fp = task.get("file_path", "")
                if fp and os.path.isfile(fp) and UPLOAD_DIR in os.path.abspath(fp):
                    try:
                        os.remove(fp)
                    except OSError:
                        pass

                # 删除整个历史目录
                task_dir = self._task_dir(task_id)
                if os.path.isdir(task_dir):
                    try:
                        shutil.rmtree(task_dir)
                    except OSError:
                        pass

                # 删除兼容的 results/ 文件
                compat_path = os.path.join(RESULT_DIR, f"{task_id}.json")
                if os.path.isfile(compat_path):
                    try:
                        os.remove(compat_path)
                    except OSError:
                        pass

                del self._tasks[task_id]
                return True
        return False


# 全局单例
task_manager = TaskManager()


def run_transcription(task_id: str, wav_path: str, engine_name: str,
                      model_name: str, language: str):
    """在后台线程中执行转录"""
    from app.engines.base import get_engine

    try:
        task_manager.update_progress(task_id, 0.05, "准备开始转录...")
        with task_manager._lock:
            if task_id in task_manager._tasks:
                task_manager._tasks[task_id]["status"] = TaskStatus.PROCESSING

        engine = get_engine(engine_name)
        if not engine:
            task_manager.fail_task(task_id, f"引擎 {engine_name} 不可用")
            return

        if not engine.is_available():
            task_manager.fail_task(
                task_id,
                f"引擎 {engine.display_name} 未安装。请运行: pip install {'openai-whisper' if engine_name == 'whisper' else 'funasr'}"
            )
            return

        def progress_cb(progress, message):
            task_manager.update_progress(task_id, progress, message)

        result = engine.transcribe(
            audio_path=wav_path,
            model_name=model_name,
            language=language if language != "auto" else None,
            progress_callback=progress_cb,
        )

        # 持久化转录用的 WAV 文件，供播放时使用（保证时间线一致）
        task_manager.persist_wav(task_id, wav_path)

        task_manager.complete_task(task_id, result.to_dict())

    except Exception as e:
        traceback.print_exc()
        task_manager.fail_task(task_id, str(e))
    finally:
        # 清理 WAV 临时转换文件（不是原始上传文件）
        if wav_path and os.path.exists(wav_path):
            task = task_manager.get_task(task_id)
            if task:
                original = task.get("file_path", "")
                media = task.get("media_file", "")
                if os.path.abspath(wav_path) not in (
                    os.path.abspath(original) if original else "",
                    os.path.abspath(media) if media else "",
                ):
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
