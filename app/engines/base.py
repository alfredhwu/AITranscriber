"""转录引擎基类与注册"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class TranscriptionSegment:
    """转录片段"""
    def __init__(self, start: float, end: float, text: str,
                 confidence: float = 1.0, speaker: str = ""):
        self.start = start
        self.end = end
        self.text = text.strip()
        self.confidence = confidence
        self.speaker = speaker

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "confidence": round(self.confidence, 3),
        }
        if self.speaker:
            d["speaker"] = self.speaker
        return d


class TranscriptionResult:
    """转录结果"""
    def __init__(self, segments: List[TranscriptionSegment], language: str = "",
                 full_text: str = "", engine: str = ""):
        self.segments = segments
        self.language = language
        self.full_text = full_text or " ".join(s.text for s in segments)
        self.engine = engine

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "language": self.language,
            "full_text": self.full_text,
            "engine": self.engine,
        }


class BaseEngine(ABC):
    """转录引擎基类"""
    name: str = ""
    display_name: str = ""
    description: str = ""
    supported_languages: List[str] = []

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    @abstractmethod
    def get_models(self) -> List[Dict[str, str]]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def transcribe(self, audio_path: str, model_name: str = "",
                   language: Optional[str] = None,
                   progress_callback=None) -> TranscriptionResult:
        """执行转录"""
        pass


# 引擎注册表
_engines: Dict[str, BaseEngine] = {}


def register_engine(engine: BaseEngine):
    _engines[engine.name] = engine


def get_engine(name: str) -> Optional[BaseEngine]:
    return _engines.get(name)


def get_all_engines() -> Dict[str, BaseEngine]:
    return _engines.copy()


def get_available_engines() -> List[Dict[str, Any]]:
    """获取所有可用引擎的信息"""
    result = []
    for name, engine in _engines.items():
        available = engine.is_available()
        result.append({
            "name": engine.name,
            "display_name": engine.display_name,
            "description": engine.description,
            "available": available,
            "models": engine.get_models() if available else [],
        })
    return result
