"""Whisper 转录引擎"""
import os
from typing import Dict, List, Any, Optional

from app.engines.base import (
    BaseEngine, TranscriptionResult, TranscriptionSegment, register_engine
)
from app.config import MODEL_CACHE_DIR


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
            import whisper
            download_root = os.path.join(MODEL_CACHE_DIR, "whisper")
            os.makedirs(download_root, exist_ok=True)
            self._model_cache[model_name] = whisper.load_model(
                model_name, download_root=download_root
            )
        return self._model_cache[model_name]

    def transcribe(self, audio_path: str, model_name: str = "base",
                   language: Optional[str] = None,
                   progress_callback=None) -> TranscriptionResult:
        import whisper

        if not model_name:
            model_name = "base"

        if progress_callback:
            progress_callback(0.1, "正在加载Whisper模型...")

        model = self._load_model(model_name)

        if progress_callback:
            progress_callback(0.3, "模型加载完成，开始转录...")

        options = {"verbose": False}
        if language and language != "auto":
            options["language"] = language

        result = model.transcribe(audio_path, **options)

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
