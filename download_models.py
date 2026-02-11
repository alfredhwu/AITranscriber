#!/usr/bin/env python3
"""
AITranscriber 模型下载脚本
自动下载 Whisper 和 FunASR 所需的全部模型
"""
import os
import sys
import argparse

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ──────────────────────────────────────────────
# Whisper 模型定义
# ──────────────────────────────────────────────
WHISPER_MODELS = {
    "tiny": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
        "size": "~75MB",
    },
    "base": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
        "size": "~145MB",
    },
    "small": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
        "size": "~480MB",
    },
    "medium": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
        "size": "~1.5GB",
    },
    "large": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
        "size": "~3GB",
    },
}

# ──────────────────────────────────────────────
# FunASR 模型定义
# ──────────────────────────────────────────────
FUNASR_MODELS = {
    "paraformer-zh": {
        "model": "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "model_revision": "v2.0.4",
        "desc": "中文 ASR 主模型",
    },
    "vad": {
        "model": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "model_revision": "v2.0.4",
        "desc": "语音端点检测 (VAD)",
    },
    "punc": {
        "model": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
        "model_revision": "v2.0.4",
        "desc": "标点恢复",
    },
    "cam++": {
        "model": "iic/speech_campplus_sv_zh-cn_16k-common",
        "model_revision": "v2.0.2",
        "desc": "说话人分离 (CAM++)",
    },
    "paraformer-en": {
        "model": "iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020",
        "model_revision": "v2.0.4",
        "desc": "英文 ASR 主模型",
    },
    "sensevoice-small": {
        "model": "iic/SenseVoiceSmall",
        "model_revision": None,
        "desc": "多语言 ASR (SenseVoice)",
    },
}

# 预设组合
FUNASR_PRESETS = {
    "zh": ["paraformer-zh", "vad", "punc", "cam++"],
    "en": ["paraformer-en", "cam++"],
    "multi": ["sensevoice-small"],
    "all": list(FUNASR_MODELS.keys()),
}


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(text):
    print(f"  → {text}")


def print_ok(text):
    print(f"  ✓ {text}")


def print_skip(text):
    print(f"  - {text}")


def print_err(text):
    print(f"  ✗ {text}", file=sys.stderr)


# ──────────────────────────────────────────────
# Whisper 下载
# ──────────────────────────────────────────────
def download_whisper_model(name: str, force: bool = False):
    """下载单个 Whisper 模型"""
    import urllib.request

    info = WHISPER_MODELS[name]
    whisper_dir = os.path.join(MODEL_DIR, "whisper")
    os.makedirs(whisper_dir, exist_ok=True)

    filename = os.path.basename(info["url"])
    filepath = os.path.join(whisper_dir, filename)

    if os.path.isfile(filepath) and not force:
        print_skip(f"{name} 已存在: {filepath}")
        return True

    print_step(f"下载 Whisper {name} ({info['size']}) ...")
    try:
        urllib.request.urlretrieve(info["url"], filepath, reporthook=_progress_hook)
        print()  # 换行
        print_ok(f"Whisper {name} 下载完成: {filepath}")
        return True
    except Exception as e:
        print_err(f"Whisper {name} 下载失败: {e}")
        if os.path.isfile(filepath):
            os.remove(filepath)
        return False


def _progress_hook(block_num, block_size, total_size):
    """下载进度回调"""
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r    [{bar}] {pct:5.1f}%  {mb_down:.1f}/{mb_total:.1f} MB", end="", flush=True)
    else:
        mb_down = downloaded / (1024 * 1024)
        print(f"\r    已下载 {mb_down:.1f} MB", end="", flush=True)


# ──────────────────────────────────────────────
# FunASR 下载 (通过 modelscope)
# ──────────────────────────────────────────────
def download_funasr_model(key: str, force: bool = False):
    """下载单个 FunASR 模型 (通过 modelscope snapshot_download)"""
    info = FUNASR_MODELS[key]
    model_id = info["model"]
    revision = info["model_revision"]

    print_step(f"下载 FunASR [{key}]: {model_id}" + (f" (revision={revision})" if revision else ""))

    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError:
        try:
            from modelscope import snapshot_download
        except ImportError:
            print_err("需要安装 modelscope: pip install modelscope")
            return False

    try:
        kwargs = {"model_id": model_id}
        if revision:
            kwargs["revision"] = revision
        local_dir = snapshot_download(**kwargs)
        print_ok(f"[{key}] 下载完成: {local_dir}")
        return True
    except Exception as e:
        print_err(f"[{key}] 下载失败: {e}")
        return False


# ──────────────────────────────────────────────
# 主逻辑
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="AITranscriber 模型下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 下载默认模型 (Whisper base + FunASR 中文全套)
  %(prog)s --whisper base small     # 下载指定 Whisper 模型
  %(prog)s --whisper all            # 下载全部 Whisper 模型
  %(prog)s --funasr zh              # 下载 FunASR 中文套件 (paraformer-zh + vad + punc + cam++)
  %(prog)s --funasr en              # 下载 FunASR 英文套件
  %(prog)s --funasr all             # 下载全部 FunASR 模型
  %(prog)s --all                    # 下载所有引擎的所有模型
  %(prog)s --whisper base --funasr zh --force  # 强制重新下载
""",
    )

    parser.add_argument(
        "--whisper",
        nargs="*",
        metavar="MODEL",
        help=f"Whisper 模型 ({', '.join(WHISPER_MODELS.keys())}, all)",
    )
    parser.add_argument(
        "--funasr",
        nargs="*",
        metavar="PRESET",
        help=f"FunASR 模型预设 (zh/en/multi/all) 或模型名 ({', '.join(FUNASR_MODELS.keys())})",
    )
    parser.add_argument("--all", action="store_true", help="下载所有模型")
    parser.add_argument("--force", action="store_true", help="强制重新下载已存在的模型")
    parser.add_argument("--list", action="store_true", help="列出所有可用模型")

    args = parser.parse_args()

    # 列出模型
    if args.list:
        print_header("Whisper 模型")
        for name, info in WHISPER_MODELS.items():
            filepath = os.path.join(MODEL_DIR, "whisper", os.path.basename(info["url"]))
            status = "已下载" if os.path.isfile(filepath) else "未下载"
            print(f"  {name:10s}  {info['size']:>8s}  [{status}]")
        print_header("FunASR 模型")
        for key, info in FUNASR_MODELS.items():
            rev = info["model_revision"] or "latest"
            print(f"  {key:20s}  {info['desc']:20s}  revision={rev}")
        print(f"\n  FunASR 预设组合:")
        for preset, models in FUNASR_PRESETS.items():
            print(f"    {preset:6s} = {', '.join(models)}")
        return

    # 默认行为：下载 Whisper base + FunASR 中文
    if not args.all and args.whisper is None and args.funasr is None:
        args.whisper = ["base"]
        args.funasr = ["zh"]
        print("未指定参数，将下载默认模型组合 (Whisper base + FunASR 中文套件)")
        print("使用 --help 查看更多选项\n")

    # 解析 Whisper 模型列表
    whisper_list = []
    if args.all or (args.whisper is not None):
        if args.all or (args.whisper is not None and "all" in args.whisper):
            whisper_list = list(WHISPER_MODELS.keys())
        elif args.whisper is not None:
            for m in args.whisper:
                if m in WHISPER_MODELS:
                    whisper_list.append(m)
                else:
                    print_err(f"未知 Whisper 模型: {m} (可选: {', '.join(WHISPER_MODELS.keys())})")
                    sys.exit(1)

    # 解析 FunASR 模型列表
    funasr_list = []
    if args.all or (args.funasr is not None):
        if args.all or (args.funasr is not None and "all" in args.funasr):
            funasr_list = list(FUNASR_MODELS.keys())
        elif args.funasr is not None:
            for item in args.funasr:
                if item in FUNASR_PRESETS:
                    funasr_list.extend(FUNASR_PRESETS[item])
                elif item in FUNASR_MODELS:
                    funasr_list.append(item)
                else:
                    print_err(f"未知 FunASR 预设/模型: {item}")
                    sys.exit(1)
            # 去重保持顺序
            seen = set()
            funasr_list = [x for x in funasr_list if not (x in seen or seen.add(x))]

    success_count = 0
    fail_count = 0

    # 下载 Whisper
    if whisper_list:
        print_header(f"下载 Whisper 模型: {', '.join(whisper_list)}")
        for name in whisper_list:
            ok = download_whisper_model(name, force=args.force)
            if ok:
                success_count += 1
            else:
                fail_count += 1

    # 下载 FunASR
    if funasr_list:
        print_header(f"下载 FunASR 模型: {', '.join(funasr_list)}")
        for key in funasr_list:
            ok = download_funasr_model(key, force=args.force)
            if ok:
                success_count += 1
            else:
                fail_count += 1

    # 汇总
    print_header("下载完成")
    print(f"  成功: {success_count}")
    if fail_count:
        print(f"  失败: {fail_count}")
    print(f"\n  模型目录: {MODEL_DIR}")
    print()

    sys.exit(1 if fail_count else 0)


if __name__ == "__main__":
    main()
