# ASR 引擎与实时接口说明

> 对接对象：MonGSV FastAPI 与 music 后端/前端。

---

## 1. 当前结论

MonGSV 现在有两条 ASR 链路，使用场景不同：

| 场景 | 使用链路 | 模型 | 是否带标点 | 推荐用途 |
|------|----------|------|------------|----------|
| 中文训练数据准备 | 离线 FunASR | `paraformer-large + fsmn-vad + ct-punc` | 是 | 中文切片的批量标注、训练前预处理 |
| 粤语训练数据准备 | 离线 FunASR | `UniASR 2-pass Cantonese` | 依模型输出 | 粤语切片的批量标注 |
| 其他支持语言训练 | Faster-Whisper | `large-v3 + float16` | 依模型输出 | 英语、日语、韩语等训练标注 |
| 实时语音识别（推荐） | `/ws/asr/final` | VAD 断句 + final ASR | 是 | 实时对话、LLM 语音输入 |
| 旧实时入口 | `/ws/asr/transcribe` | VAD + 声纹门禁 + final ASR | 自动补标点 | 兼容旧路径，不再返回 interim |
| 多语言单文件转录 | Faster-Whisper | `faster-whisper-*` | 依模型输出 | 非中文/自动语言检测 |

**训练 ASR 不使用 `paraformer-zh-streaming`。** streaming 模型是实时场景用的，直接用于训练标注容易出现重复字、漏字、无标点等问题。

---

## 2. 训练 ASR

训练流程中的 ASR 由 `asr_recognition` 服务执行：

```text
音频切片
 -> ASR 识别
 -> 文本处理
 -> 音频特征
 -> 语义编码
 -> GPT / SoVITS 训练
```

中文默认配置：

```text
model_type = funasr
language = zh
```

实际加载：

```text
speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
+ speech_fsmn_vad_zh-cn-16k-common-pytorch
+ punc_ct-transformer_zh-cn-common-vocab272727-pytorch
```

训练工作流按语言自动选择引擎：

| `language` | 实际引擎 |
|------------|----------|
| `zh` | FunASR Paraformer-large + FSMN VAD +中文标点模型 |
| `yue` | FunASR UniASR 2-pass Cantonese |
| `en`、`ja`、`ko` 等 | Faster-Whisper large-v3 + float16 |

输出 `.list` 格式：

```text
audio_path|speaker|language|text
```

`speaker` 当前取输入文件或目录名，`language` 写成大写代码。独立调用 `/data-prep/asr/recognize` 时，`output_file` 只是输出位置提示：如果传入 `.list` 路径，当前实现只使用其父目录，实际文件名必须读取响应中的 `output_file`。

特点：

- 适合训练标注。
- 识别结果自带中文标点。
- 会通过 VAD/标点模型提升完整句质量。
- 失败时工作流会停止，并输出缺失项/失败原因，避免只切分完就直接进入训练。

### 当前参数边界

HTTP 模型暴露了 `model_size`、`precision`、`batch_size`、`beam_size`、`vad_filter`，但统一服务目前只把 `model_type` 和 `language` 继续传到底层。Faster-Whisper 实际使用 `large-v3 + float16 + beam_size=5 + VAD`；其他参数目前主要用于配置校验或驻留键，不能当作已经生效的推理调参。

`/inference/transcribe/models/load` 当前只准备统一引擎并登记驻留状态，大模型权重仍在第一次识别时延迟加载，不是完整的显存预热。

---

## 3. 实时 ASR

推荐实时接口：

```text
ws://host:40302/ws/asr/final
```

连接成功后，后端会立即返回：

```json
{"type":"connection","status":"connected","message":"VAD final STT 已就绪","protocol":"vad-final-speaker-gate-v1","speaker_gate":"required"}
```

`/ws/asr/final` 使用 VAD 判断一句话结束，先与当前用户的已登记声纹做 1:1 验证，通过后才把该段 PCM 送入 final ASR。它会保留约 1.2 秒前置音频，避免 VAD 从 `speech=false` 切到 `speech=true` 之前的开头人声被丢弃。

音频输入要求：

| 项 | 要求 |
|----|------|
| 格式 | 裸 PCM 二进制 |
| 采样率 | `16000 Hz` |
| 声道 | 单声道 |
| 位深 | signed int16 |
| 字节序 | little-endian |

调用流程：

```text
1. 建立 WebSocket
2. 发送包含当前用户 `speaker_id` 的 `start`，可选携带 VAD 断句参数
3. 持续发送 PCM int16 二进制帧
4. 持续接收 audio_state / voice_activity
5. VAD 断句后接收 result / commit_hint
6. 结束时发送 {"command":"stop"}
7. 接收 final_text
```

启动时可以由调用方决定断句参数：

```json
{
  "command": "start",
  "speaker_id": "music-user-123",
  "vad": {
    "chunk_ms": 200,
    "end_silence_ms": 1200,
    "speech_noise_threshold": 0.6,
    "min_speech_duration_ms": 250,
    "preroll_ms": 1200
  }
}
```

如果只需要让 MonCore 的静音设置生效，也可以只传：

```json
{
  "command": "start",
  "speaker_id": "music-user-123",
  "end_silence_ms": 1200
}
```

严格声纹门禁下，两个 WebSocket 接口都不会返回 interim。只有完整 VAD 段通过声纹验证后，才返回 `is_interim=false` 的最终段落。

音频状态：

```json
{
  "type": "audio_state",
  "input_level": 0.42,
  "noise_level": 0.08,
  "clipping": false
}
```

人声活动：

```json
{
  "type": "voice_activity",
  "is_speech": true,
  "silence_ms": 0,
  "speech_ms": 1200
}
```

声纹不匹配时返回门禁事件，不返回文本：

```json
{
  "type": "speaker_gate",
  "accepted": false,
  "code": "VOICEPRINT_MISMATCH",
  "speaker_id": "music-user-123",
  "speaker_similarity": 0.41
}
```

返回最终段落：

```json
{
  "type": "result",
  "text": "最终识别文本，带标点。",
  "accumulated": "累计最终文本，带标点。",
  "is_interim": false,
  "sentence_end": true
}
```

提交建议：

```json
{
  "type": "commit_hint",
  "reason": "silence",
  "should_commit": true,
  "final_text": "完整最终文本，带标点。",
  "vad": {
    "end_silence_ms": 1200,
    "actual_silence_ms": 1200
  }
}
```

`commit_hint` 不直接代表发送聊天消息，只表示 GSV 建议 MonCore/前端可以提交。

声纹门禁强制开启：未注册、不匹配、有效语音过短或声纹服务异常时均按拒绝处理，ASR 不会执行。`speaker_id` 必须由完成身份认证的 music 后端注入，不能信任浏览器自行声明的 ID。

停止后返回：

```json
{
  "type": "status",
  "message": "录音结束",
  "final_text": "完整最终文本，带标点。"
}
```

### 403 握手排查

当前 `/ws/asr/final` 和 `/ws/asr/transcribe` 不做 token 鉴权，也不限制 Origin。若 `GET /health`、`/docs` 正常，但 WebSocket 握手返回 `HTTP 403 Forbidden`，同时普通 HTTP GET WebSocket 路径返回 `404 Not Found`，通常不是 MonCore 代理链路问题，而是 GSV 后端没有跑到正确的 WebSocket 路由。

优先检查：

```bash
grep -RIn "ws/asr/final\\|ws/asr/transcribe\\|websocket: WebSocket" Code/FastApi/Base/Gateway
pm2 describe MonGsvBackend
pm2 logs MonGsvBackend --lines 80 --nostream
```

正确的 PM2 后端应启动统一网关入口，并且握手日志应显示：

```text
"WebSocket /ws/asr/final" [accepted]
connection open
```

---

## 4. 为什么训练不用 streaming

`paraformer-zh-streaming` 是在线流式模型，推荐按固定 chunk 连续输入，并维护 cache。它更适合“边说边显示”的场景。

中文训练标注需要的是稳定、完整、带标点的句子，因此使用离线 FunASR Paraformer-large 更合适。非中文训练则由工作流分流到 Faster-Whisper。

实测同一批切片：

```text
streaming 修复前：我还个个会会会认是这你你不会我们们需要我哥道为
streaming 修复后：我还记得这件会议室这是专门为特雷西亚控制的位置吗
funasr_large：我还记得这间会议室，这是专门为特雷西亚控制的位置吗？
```

所以推荐：

```text
中文训练标注：FunASR Paraformer-large
粤语训练标注：FunASR UniASR 2-pass Cantonese
其他支持语言训练标注：Faster-Whisper large-v3
实时交互：paraformer-zh-streaming + final 标点恢复
```

---

## 5. 本项目与 funasr-back 对比

| 维度 | MonGSV FastAPI | funasr-back |
|------|----------------|-------------|
| 后端框架 | FastAPI + Uvicorn | Django + Daphne |
| 训练 ASR | `paraformer-large + VAD + PUNC` | 无训练链路 |
| 实时 ASR | `/ws/asr/final`，或 `/ws/asr/transcribe` | `ws/voice/transcribe/` |
| 实时模型 | `paraformer-zh-streaming` | `paraformer-zh-streaming` |
| 标点恢复 | final 阶段 `ct-punc` | 独立标点模型 |
| 声纹识别 | 支持注册/识别/验证接口 | 支持 |
| TTS 训练/推理 | 支持完整链路 | 不负责 |

---

## 6. 对接建议

music 后端/前端建议这样用：

| 需求 | 调用接口 |
|------|----------|
| 上传音频并训练角色 | `/workflow/training/full` 或 `/workflow/complete` |
| 单文件转录 | `/inference/transcribe` |
| 实时麦克风识别/对话输入 | `/ws/asr/final` |
| 旧实时入口 | `/ws/asr/transcribe`（声纹验证后仅返回 final） |
| 训练数据批量 ASR | `/data-prep/asr/recognize` |

前端不要自己决定训练 ASR 模型，只需要传：

```text
world
version
role
language
raw audio
```

后端会按 `language` 自动选择 FunASR 或 Faster-Whisper 完成训练标注。
