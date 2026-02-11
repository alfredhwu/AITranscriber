"""FunASR 转录引擎"""
import os
from typing import Dict, List, Any, Optional

from app.engines.base import (
    BaseEngine, TranscriptionResult, TranscriptionSegment, register_engine
)
from app.config import MODEL_CACHE_DIR


class FunASREngine(BaseEngine):
    name = "funasr"
    display_name = "FunASR (阿里达摩院)"
    description = "阿里达摩院开源语音识别模型，中文效果优秀，支持标点恢复与时间戳"
    supported_languages = ["zh", "en", "ja", "ko"]

    _pipeline_cache = {}

    def is_available(self) -> bool:
        try:
            from funasr import AutoModel
            return True
        except Exception:
            return False

    def get_models(self) -> List[Dict[str, str]]:
        return [
            {
                "id": "paraformer-zh",
                "name": "Paraformer-zh",
                "description": "中文语音识别，高精度，带时间戳与标点"
            },
            {
                "id": "paraformer-en",
                "name": "Paraformer-en",
                "description": "英文语音识别"
            },
            {
                "id": "sensevoice-small",
                "name": "SenseVoice-Small",
                "description": "多语言语音识别，轻量高效"
            },
        ]

    def _get_model_config(self, model_name: str) -> Dict[str, Any]:
        configs = {
            "paraformer-zh": {
                "model": "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                "vad_model": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                "punc_model": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
                "spk_model": "cam++",
            },
            "paraformer-en": {
                "model": "iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020",
                "spk_model": "cam++",
            },
            "sensevoice-small": {
                "model": "iic/SenseVoiceSmall",
            },
        }
        return configs.get(model_name, configs["paraformer-zh"])

    def _load_pipeline(self, model_name: str):
        if model_name not in self._pipeline_cache:
            from funasr import AutoModel

            cache_dir = os.path.join(MODEL_CACHE_DIR, "funasr")
            os.makedirs(cache_dir, exist_ok=True)

            config = self._get_model_config(model_name)

            kwargs = {"model": config["model"], "model_revision": "v2.0.4"}
            if "vad_model" in config:
                kwargs["vad_model"] = config["vad_model"]
                kwargs["vad_model_revision"] = "v2.0.4"
            if "punc_model" in config:
                kwargs["punc_model"] = config["punc_model"]
                kwargs["punc_model_revision"] = "v2.0.4"
            if "spk_model" in config:
                kwargs["spk_model"] = config["spk_model"]
                kwargs["spk_model_revision"] = "v2.0.2"

            self._pipeline_cache[model_name] = AutoModel(**kwargs)

        return self._pipeline_cache[model_name]

    def transcribe(self, audio_path: str, model_name: str = "paraformer-zh",
                   language: Optional[str] = None,
                   progress_callback=None) -> TranscriptionResult:

        if not model_name:
            model_name = "paraformer-zh"

        if progress_callback:
            progress_callback(0.1, "正在加载FunASR模型...")

        pipeline = self._load_pipeline(model_name)

        if progress_callback:
            progress_callback(0.3, "模型加载完成，开始转录...")

        result = pipeline.generate(input=audio_path)

        if progress_callback:
            progress_callback(0.9, "转录完成，正在处理结果...")

        segments = []

        if result and len(result) > 0:
            res = result[0]
            text = res.get("text", "")

            # FunASR may return sentence-level info in different keys
            sentence = res.get("sentence_info", None) or res.get("sentences", None)

            if sentence and isinstance(sentence, list) and len(sentence) > 0:
                for sent in sentence:
                    s_start = sent.get("start", sent.get("begin", 0))
                    s_end = sent.get("end", 0)
                    s_text = sent.get("text", sent.get("content", ""))
                    s_speaker = sent.get("spk", sent.get("speaker", ""))
                    if isinstance(s_speaker, int):
                        s_speaker = f"说话人 {s_speaker + 1}"
                    elif s_speaker:
                        s_speaker = str(s_speaker)
                    # FunASR timestamps may be in milliseconds
                    if s_start > 1000 or s_end > 1000:
                        s_start = s_start / 1000.0
                        s_end = s_end / 1000.0
                    segments.append(TranscriptionSegment(
                        start=s_start,
                        end=s_end,
                        text=s_text,
                        speaker=s_speaker,
                    ))
            elif "timestamp" in res and res["timestamp"]:
                timestamps = res["timestamp"]
                # timestamps is typically a list of [start_ms, end_ms] pairs
                # We need to match them with text characters/words
                if isinstance(timestamps, list) and len(timestamps) > 0:
                    if isinstance(timestamps[0], (list, tuple)):
                        # Group timestamps into sentence-level chunks (~5s each)
                        chunk_segments = self._group_timestamps_with_text(timestamps, text)
                        segments.extend(chunk_segments)
                    elif isinstance(timestamps[0], dict):
                        for ts in timestamps:
                            segments.append(TranscriptionSegment(
                                start=ts.get("start", 0) / 1000.0,
                                end=ts.get("end", 0) / 1000.0,
                                text=ts.get("text", ""),
                            ))
            
            # Fallback: if no segments were created but we have text
            if not segments and text:
                segments.append(TranscriptionSegment(
                    start=0.0,
                    end=0.0,
                    text=text,
                ))

        detected_lang = language or "zh"
        return TranscriptionResult(
            segments=segments,
            language=detected_lang,
            engine=f"funasr-{model_name}",
        )

    @staticmethod
    def _group_timestamps_with_text(timestamps, text):
        """Group character-level timestamps with text into sentence-level segments."""
        from app.engines.base import TranscriptionSegment

        if not timestamps or not text:
            return []

        segments = []
        chars = list(text.replace(" ", ""))
        
        # Punctuation marks that indicate sentence boundaries
        sentence_ends = set("。！？；.!?;，,")
        
        chunk_text = ""
        chunk_start = None
        chunk_end = None
        
        for i, ts in enumerate(timestamps):
            if isinstance(ts, (list, tuple)) and len(ts) >= 2:
                start_ms, end_ms = ts[0], ts[1]
            else:
                continue
                
            if chunk_start is None:
                chunk_start = start_ms
            chunk_end = end_ms
            
            # Get corresponding character if available
            if i < len(chars):
                chunk_text += chars[i]
            
            # Create a segment at sentence boundaries or every ~20 characters
            is_sentence_end = (i < len(chars) and chars[i] in sentence_ends)
            is_chunk_long = len(chunk_text) >= 20
            is_last = (i == len(timestamps) - 1)
            
            if (is_sentence_end or is_chunk_long or is_last) and chunk_text.strip():
                segments.append(TranscriptionSegment(
                    start=chunk_start / 1000.0,
                    end=chunk_end / 1000.0,
                    text=chunk_text.strip(),
                ))
                chunk_text = ""
                chunk_start = None
                chunk_end = None
        
        # Handle any remaining text
        if chunk_text.strip() and chunk_start is not None:
            segments.append(TranscriptionSegment(
                start=chunk_start / 1000.0,
                end=(chunk_end or chunk_start) / 1000.0,
                text=chunk_text.strip(),
            ))
        
        return segments


register_engine(FunASREngine())
