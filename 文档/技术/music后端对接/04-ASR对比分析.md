# ASR 引擎对比分析

> 对比对象：**本项目**（MonGSV FastAPI） vs **funasr-back**（参考仓库）

---

## 1. 架构对比

| 维度 | 本项目 (MonGSV) | funasr-back |
|------|----------------|-------------|
| **技术栈** | FastAPI + Uvicorn | Django 6.0 + Daphne (ASGI) |
| **ASR 引擎数** | 双引擎：FunASR + Faster-Whisper | 单引擎：FunASR (Paraformer-streaming) |
| **VAD** | FunASR 内置 FSMN-VAD | Silero VAD + 自研 VAD（双 VAD 策略） |
| **标点恢复** | FunASR 内置 CT-Transformer | CT-Transformer（独立加载） |
| **声纹识别** | 无 | ERes2Net（ModelScope） |
| **WebSocket** | 无 | 支持（Channels） |
| **模型驻留** | ModelResidencyManager（超时淘汰） | 无（全局单例常驻） |
| **并发控制** | 线程锁 + 请求计数 | 无（单线程 ASGI） |

---

## 2. ASR 模型对比

### 本项目

**引擎一：FunASR（默认）**
- 模型：`Paraformer-large`（非流式）
- 路径：`tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/`
- 支持语言：中文、粤语
- VAD：`speech_fsmn_vad_zh-cn-16k-common-pytorch`
- 标点：`punc_ct-transformer_zh-cn-common-vocab272727-pytorch`
- 模型源：ModelScope

**引擎二：Faster-Whisper（备选）**
- 模型：`Systran/faster-whisper-{large-v3/large-v2/medium...}`
- 支持语言：99 种（含 auto 自动检测）
- 中文场景自动 fallback 到 FunASR 以获得更好精度
- 模型源：HuggingFace / ModelScope

**调度逻辑：**
```python
if 语言 in ("zh", "yue"):
    走 FunASR（默认）
else:
    走 Faster-Whisper
    如果检测到中文片段 → fallback 到 FunASR
```

### funasr-back

- 模型：`Paraformer-zh-streaming`（流式版）
- 路径：FunASR AutoModel 自动管理
- 支持语言：中文为主
- VAD：Silero VAD + 自研 VAD 双重检测
- 标点：`ct-punc-c`（独立加载）
- 模型源：FunASR / ModelScope
- 支持流式推理（2-pass：interim 实时 + final 确认）

---

## 3. API 差异

### 本项目 HTTP API

| 端点 | 功能 | 请求格式 |
|------|------|----------|
| `POST /data-prep/asr/recognize` | 批量音频目录 ASR | form-data: `audio_dir`, `output_file`, `language` |
| `POST /inference/transcribe` | 单文件轻量转录 | form-data: `audio_file` 上传, `language` |
| `POST /inference/transcribe/models/load` | 预加载 ASR 模型 | form-data: `model_type`, `model_size`, `language` |
| `GET /inference/transcribe/models/info` | 模型信息 | - |
| `POST /inference/transcribe/models/unload` | 卸载模型 | - |

### funasr-back HTTP API

| 端点 | 功能 | 请求格式 |
|------|------|----------|
| `POST /voice/transcribe/` | 单文件 ASR | form-data: `audio` 上传 |
| `POST /voice/speaker/register/` | 注册说话人声纹 | form-data: `audio`, `speaker_id`, `name` |
| `POST /voice/speaker/unregister/` | 注销说话人 | form-data: `speaker_id` |
| `GET /voice/speaker/list/` | 列出说话人 | - |
| `POST /voice/speaker/identify/` | 识别说话人 | form-data: `audio`, `threshold` |
| `POST /voice/speaker/verify/` | 验证两段音频 | form-data: `audio1`, `audio2` |
| `POST /voice/diarize/` | 说话人日志 | form-data: `audio`, `language`, `threshold` |

### funasr-back WebSocket API

| 端点 | 功能 |
|------|------|
| `ws/voice/transcribe/` | 实时流式 ASR（2-pass：interim 实时片段 + final 精确确认） |
| `ws/voice/vad/` | 实时 VAD 检测 |

---

## 4. 核心代码量

| 模块 | 本项目 | funasr-back |
|------|--------|-------------|
| ASR 引擎 | `tools/asr/funasr_asr.py` 201行 | `engines/asr.py` ~120行 |
| | `tools/asr/fasterwhisper_asr.py` 266行 | |
| ASR 服务层 | `Code/.../asr_recognition/service.py` 524行 | `services/voice_service.py` ~200行 |
| | 含模型驻留、并发控制 | 全局单例，懒加载 |
| WebSocket | 无 | `consumers/asr_consumer.py` ~270行 |
| 声纹识别 | 无 | `engines/speaker.py` ~50行 |
| | | `services/speaker_db.py` ~100行 |

---

## 5. 模型文件缓存

### 本项目

```
tools/asr/models/
├── speech_fsmn_vad_zh-cn-16k-common-pytorch/     (VAD)
├── punc_ct-transformer_zh-cn-common-vocab272727-pytorch/  (标点)
├── speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/  (ASR)
├── speech_UniASR_asr_2pass-cantonese-CHS-16k-common-vocab1468-tensorflow1-online/  (粤语)
├── faster-whisper-large-v3/     (Whisper 备选)
└── ...
```

通过 `ensure_snapshot()` 函数管理，检查本地文件后决定是否从 ModelScope 下载。

### funasr-back

通过 FunASR `AutoModel` 自动管理模型缓存，不显式指定本地路径。

---

## 6. 流式 vs 非流式

| 特性 | 本项目 | funasr-back |
|------|--------|-------------|
| 推理方式 | **非流式**（完整音频一次性处理） | 支持**流式**（WebSocket 实时） |
| 实时性 | 适合后处理、训练数据准备 | 适合实时对话、语音交互 |
| 分片策略 | 无（整个文件输入） | `chunk_size=[0,5,5]` 流式分片 |
| 中间结果 | 无 | 2-pass：interim（实时片段）+ final（确认） |

---

## 7. 版权与许可

两者均使用相同的基础模型，依赖 ModelScope / HuggingFace 上的开源模型，许可兼容。

关键依赖：
```
本项目: funasr==1.0.27
funasr-back: funasr>=1.3.1
```

---

## 8. 总结

| 你需要... | 用本项目 | 用 funasr-back |
|-----------|----------|----------------|
| 中文批量音频转文字（训练数据准备） | 适合 | 也可 |
| 多语言 ASR（英/日/韩等） | 适合（Faster-Whisper） | 不适合 |
| 实时流式语音识别 | 不适合 | 适合（WebSocket） |
| 声纹注册/识别/验证 | 不适合 | 适合 |
| 说话人日志（谁在什么时候说话） | 不适合 | 适合 |
| TTS 全链路（数据→训练→推理） | 适合 | 不适合 |

**一句话：本项目 ASR 是为 TTS 数据准备服务的配角，funasr-back 是专业 ASR + 声纹的独立服务。** (｀・ω・´)
