# AITranscriber 安装说明

## 系统要求

- **操作系统**: macOS 10.15+ / Windows 10+
- **Python**: 3.8+（仅源码运行需要）
- **FFmpeg**: 必须安装并加入系统 PATH
- **磁盘空间**: 至少 500MB（不含模型文件）
- **内存**: 建议 8GB+（大模型需要更多）

---

## 方式一：安装包运行（推荐）

### macOS

1. 解压 `AITranscriber-macOS.tar.gz`
2. 安装 FFmpeg（如果尚未安装）：
   ```bash
   brew install ffmpeg
   ```
3. 双击 `启动AITranscriber.command` 即可运行
4. 浏览器会自动打开 `http://127.0.0.1:8765`

> 首次打开可能提示"无法验证开发者"，前往 **系统设置 > 隐私与安全性**，点击"仍然允许"。

### Windows

1. 在 Windows 机器上执行 `build_windows.bat` 完成打包
2. 解压或进入 `dist\AITranscriber-Windows\` 目录
3. 安装 FFmpeg：
   - 从 https://ffmpeg.org/download.html 下载
   - 将 `ffmpeg.exe` 所在目录加入系统 PATH
4. 双击 `启动AITranscriber.bat` 运行
5. 浏览器会自动打开 `http://127.0.0.1:8765`

---

## 方式二：源码运行

### macOS / Linux

```bash
# 克隆项目
cd AITranscriber

# 安装 FFmpeg
brew install ffmpeg          # macOS
# sudo apt install ffmpeg    # Ubuntu/Debian

# 一键启动（自动创建虚拟环境并安装依赖）
chmod +x start.sh
./start.sh
```

### Windows

```cmd
cd AITranscriber

:: 一键启动（自动创建虚拟环境并安装依赖）
start.bat
```

---

## 方式三：手动安装

```bash
cd AITranscriber

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate.bat    # Windows

# 安装依赖
pip install -r requirements.txt

# 启动
python run.py
```

---

## 自行打包

如需在当前平台生成安装包：

### macOS

```bash
chmod +x build_macos.sh
./build_macos.sh
```

输出：`dist/AITranscriber-macOS.tar.gz`

### Windows

```cmd
build_windows.bat
```

输出：`dist\AITranscriber-Windows\`

> PyInstaller 打包必须在目标平台上执行，不支持交叉编译。

---

## 转录引擎与模型说明

模型文件在首次使用时自动下载，缓存在程序目录下的 `models/` 文件夹中。

### OpenAI Whisper

多语言语音识别，精度高。模型缓存路径：`models/whisper/`

| 模型 | 大小 | 显存需求 | 说明 |
|------|------|---------|------|
| tiny | ~75MB | ~1GB | 最快速度，最低精度 |
| base | ~145MB | ~1GB | 快速，基本精度 |
| small | ~480MB | ~2GB | 平衡速度与精度 |
| medium | ~1.5GB | ~5GB | 较高精度 |
| large | ~3GB | ~10GB | 最高精度 |

支持语言：自动检测、中文、英文、日语、韩语、法语、德语、西班牙语、俄语

### FunASR（阿里达摩院）

中文效果优秀，支持标点恢复、时间戳与说话人识别。模型缓存路径：`models/funasr/`

**可选模型：**

| 模型 | 模型 ID | 说明 |
|------|---------|------|
| Paraformer-zh | paraformer-zh | 中文语音识别，高精度，带时间戳与标点 |
| Paraformer-en | paraformer-en | 英文语音识别 |
| SenseVoice-Small | sensevoice-small | 多语言语音识别，轻量高效 |

支持语言：中文、英文、日语、韩语

**Paraformer-zh 使用的子模型（自动下载，版本 v2.0.4）：**

| 子模型 | ModelScope ID | 用途 |
|--------|--------------|------|
| ASR 主模型 | `iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch` | 语音识别 |
| VAD 模型 | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | 语音端点检测 |
| 标点模型 | `iic/punc_ct-transformer_cn-en-common-vocab471067-large` | 标点恢复 |
| 说话人模型 | `cam++`（版本 v2.0.2） | 说话人分离 |

**Paraformer-en 使用的子模型：**

| 子模型 | ModelScope ID | 用途 |
|--------|--------------|------|
| ASR 主模型 | `iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020` | 语音识别 |
| 说话人模型 | `cam++`（版本 v2.0.2） | 说话人分离 |

**SenseVoice-Small 使用的子模型：**

| 子模型 | ModelScope ID | 用途 |
|--------|--------------|------|
| ASR 主模型 | `iic/SenseVoiceSmall` | 多语言语音识别 |

> FunASR 模型从 ModelScope 下载，Whisper 模型从 HuggingFace 下载。国内用户如下载缓慢，可配置代理或参考下方手动下载说明。

---

## 手动下载模型

如果自动下载失败或网络缓慢，可按以下方式手动下载模型。

### Whisper 模型

模型存放路径：`models/whisper/`

```bash
# 以 base 模型为例，替换 base 为所需模型名 (tiny/base/small/medium/large)
# 下载地址格式：https://openaipublic.azureedge.net/main/whisper/models/<hash>/<name>.pt

# tiny
curl -L -o models/whisper/tiny.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"

# base
curl -L -o models/whisper/base.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt"

# small
curl -L -o models/whisper/small.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt"

# medium
curl -L -o models/whisper/medium.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt"

# large
curl -L -o models/whisper/large-v3.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt"
```

> Windows 用户可将上述 URL 粘贴到浏览器直接下载，然后将 `.pt` 文件放入 `models\whisper\` 目录。

### FunASR 模型

FunASR 模型从 ModelScope 下载。可以使用 `modelscope` 命令行工具手动下载：

```bash
# 安装 modelscope CLI（如果尚未安装）
pip install modelscope

# 下载 Paraformer-zh 主模型
modelscope download --model iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch --revision v2.0.4

# 下载 VAD 模型
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch --revision v2.0.4

# 下载标点恢复模型
modelscope download --model iic/punc_ct-transformer_cn-en-common-vocab471067-large --revision v2.0.4

# 下载说话人分离模型 (CAM++)
modelscope download --model iic/speech_campplus_sv_zh-cn_16k-common --revision v2.0.2

# 下载 Paraformer-en 主模型（如需英文识别）
modelscope download --model iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020 --revision v2.0.4

# 下载 SenseVoice-Small（如需多语言识别）
modelscope download --model iic/SenseVoiceSmall
```

也可以从 ModelScope 网页手动下载：

| 模型 | 下载地址 |
|------|---------|
| Paraformer-zh 主模型 | https://modelscope.cn/models/iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch |
| VAD 模型 | https://modelscope.cn/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch |
| 标点恢复模型 | https://modelscope.cn/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large |
| 说话人分离模型 | https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common |
| Paraformer-en 主模型 | https://modelscope.cn/models/iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020 |
| SenseVoice-Small | https://modelscope.cn/models/iic/SenseVoiceSmall |

> FunASR 模型下载后默认缓存在 `~/.cache/modelscope/hub/` 目录下，程序会自动检索，无需手动移动。

---

## 常见问题

**Q: 提示"未检测到 ffmpeg"**
A: 请按上方说明安装 FFmpeg 并确保其在系统 PATH 中。验证：终端运行 `ffmpeg -version`。

**Q: macOS 提示无法打开**
A: 前往 系统设置 > 隐私与安全性，找到被阻止的应用点击"仍然允许"。或在终端中直接运行 `./AITranscriber`。

**Q: 端口 8765 被占用**
A: 修改 `app/config.py` 中的 `PORT` 值，或关闭占用该端口的程序。

**Q: 模型下载慢**
A: 参考上方「手动下载模型」章节，使用命令行工具或浏览器直接下载。国内用户也可配置代理加速：`export HTTPS_PROXY=http://your-proxy:port`。
