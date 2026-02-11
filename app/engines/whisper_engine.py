"""Whisper 转录引擎"""
import os
import logging
from typing import Dict, List, Any, Optional

from app.engines.base import (
    BaseEngine, TranscriptionResult, TranscriptionSegment, register_engine
)
from app.config import MODEL_CACHE_DIR

logger = logging.getLogger(__name__)


class WhisperEngine(BaseEngine):
    name = "whisper"
    display_name = "OpenAI Whisper"
    description = "OpenAI开源语音识别模型，支持多语言，精度高"
    supported_languages = ["auto", "zh", "en", "ja", "ko", "fr", "de", "es", "ru"]

    _model_cache = {}

    def is_available(self) -> bool:
        try:
            import whisper
            return True
        except Exception:
            return False

    def get_models(self) -> List[Dict[str, str]]:
        return [
            {"id": "tiny", "name": "Tiny", "description": "最快速度，最低精度 (~1GB显存)"},
            {"id": "base", "name": "Base", "description": "快速，基本精度 (~1GB显存)"},
            {"id": "small", "name": "Small", "description": "平衡速度与精度 (~2GB显存)"},
            {"id": "medium", "name": "Medium", "description": "较高精度 (~5GB显存)"},
            {"id": "large", "name": "Large", "description": "最高精度 (~10GB显存)"},
        ]

    def _load_model(self, model_name: str):
        if model_name not in self._model_cache:
            # 1. 校验 whisper 包可用
            try:
                import whisper
            except ImportError as e:
                raise RuntimeError(
                    f"Whisper 未安装或导入失败: {e}。请运行: pip install openai-whisper"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Whisper 加载异常: {e}"
                ) from e

            download_root = os.path.join(MODEL_CACHE_DIR, "whisper")
            os.makedirs(download_root, exist_ok=True)

            logger.info(f"[Whisper] 加载模型 {model_name}, 缓存目录: {download_root}")

            # 2. 校验模型加载
            try:
                model = whisper.load_model(model_name, download_root=download_root)
            except FileNotFoundError as e:
                raise RuntimeError(
                    f"Whisper 模型文件缺失 ({model_name}): {e}。"
                    f"请运行: python download_models.py --whisper {model_name}"
                ) from e
            except ConnectionError as e:
                raise RuntimeError(
                    f"Whisper 模型下载失败 ({model_name}): {e}。请检查网络连接或手动下载模型。"
                ) from e
            except RuntimeError as e:
                raise RuntimeError(
                    f"Whisper 模型 {model_name} 加载失败: {e}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Whisper 模型 {model_name} 加载失败: {type(e).__name__}: {e}"
                ) from e

            if model is None:
                raise RuntimeError(
                    f"Whisper 模型 {model_name} 加载返回 None，请检查模型文件完整性。"
                )

            logger.info(f"[Whisper] 模型 {model_name} 加载成功")
            self._model_cache[model_name] = model

        return self._model_cache[model_name]

    def transcribe(self, audio_path: str, model_name: str = "base",
                   language: Optional[str] = None,
                   progress_callback=None) -> TranscriptionResult:

        if not model_name:
            model_name = "base"

        # 校验模型名称
        valid_models = {m["id"] for m in self.get_models()}
        if model_name not in valid_models:
            raise ValueError(
                f"不支持的 Whisper 模型: {model_name}，可选: {', '.join(valid_models)}"
            )

        if progress_callback:
            progress_callback(0.1, "正在加载Whisper模型...")

        try:
            model = self._load_model(model_name)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Whisper 模型加载失败: {type(e).__name__}: {e}") from e

        if progress_callback:
            progress_callback(0.3, "模型加载完成，开始转录...")

        # 校验音频文件
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        options = {"verbose": False}
        if language and language != "auto":
            options["language"] = language

        try:
            result = model.transcribe(audio_path, **options)
        except Exception as e:
            raise RuntimeError(
                f"Whisper 转录执行失败 ({model_name}): {type(e).__name__}: {e}"
            ) from e

        if progress_callback:
            progress_callback(0.9, "转录完成，正在处理结果...")

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptionSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                confidence=seg.get("avg_logprob", 0),
                speaker=seg.get("speaker", ""),
            ))

        detected_lang = result.get("language", language or "")

        return TranscriptionResult(
            segments=segments,
            language=detected_lang,
            engine=f"whisper-{model_name}",
        )


register_engine(WhisperEngine())
