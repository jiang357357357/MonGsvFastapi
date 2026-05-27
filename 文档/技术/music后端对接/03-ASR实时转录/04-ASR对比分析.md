# ASR 引擎与实时接口说明

> 对接对象：MonGSV FastAPI 与 music 后端/前端。

---

## 1. 当前结论

MonGSV 现在有两条 ASR 链路，使用场景不同：

| 场景 | 使用链路 | 模型 | 是否带标点 | 推荐用途 |
|------|----------|------|------------|----------|
| 训练数据准备 | 离线 ASR | `paraformer-large + fsmn-vad + ct-punc` | 是 | 切片后的批量标注、训练前预处理 |
| 实时语音识别 | WebSocket streaming | `paraformer-zh-streaming` | final 阶段补标点 | 实时对话、语音输入、前端麦克风 |
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

默认配置：

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

输出 `.list` 格式：

```text
audio_path|speaker|language|text
```

特点：

- 适合训练标注。
- 识别结果自带中文标点。
- 会通过 VAD/标点模型提升完整句质量。
- 失败时工作流会停止，并输出缺失项/失败原因，避免只切分完就直接进入训练。

---

## 3. 实时 ASR

实时接口：

```text
ws://host:40302/ws/asr/transcribe
```

连接成功后，后端会立即返回：

```json
{"type":"connection","status":"connected","message":"2-pass 流式识别已就绪"}
```

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
2. 发送 {"command":"start"}
3. 持续发送 PCM int16 二进制帧
4. 接收 is_interim=true 的实时片段
5. 结束时发送 {"command":"stop"}
6. 接收 final_text
```

返回实时片段：

```json
{
  "type": "result",
  "text": "实时识别文本",
  "accumulated": "实时识别文本",
  "is_interim": true,
  "sentence_end": false
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

停止后返回：

```json
{
  "type": "status",
  "message": "录音结束",
  "final_text": "完整最终文本，带标点。"
}
```

### 403 握手排查

当前 `/ws/asr/transcribe` 不做 token 鉴权，也不限制 Origin。若 `GET /health`、`/docs` 正常，但 WebSocket 握手返回 `HTTP 403 Forbidden`，同时普通 HTTP GET `/ws/asr/transcribe` 返回 `404 Not Found`，通常不是 MonCore 代理链路问题，而是 GSV 后端没有跑到正确的 WebSocket 路由。

优先检查：

```bash
grep -RIn "ws/asr/transcribe\\|websocket: WebSocket" Code/FastApi/Base/Gateway
pm2 describe MonGsvBackend
pm2 logs MonGsvBackend --lines 80 --nostream
```

正确的 PM2 后端应启动统一网关入口，并且握手日志应显示：

```text
"WebSocket /ws/asr/transcribe" [accepted]
connection open
```

---

## 4. 为什么训练不用 streaming

`paraformer-zh-streaming` 是在线流式模型，推荐按固定 chunk 连续输入，并维护 cache。它更适合“边说边显示”的场景。

训练标注需要的是稳定、完整、带标点的句子，因此使用离线 `funasr_large` 更合适。

实测同一批切片：

```text
streaming 修复前：我还个个会会会认是这你你不会我们们需要我哥道为
streaming 修复后：我还记得这件会议室这是专门为特雷西亚控制的位置吗
funasr_large：我还记得这间会议室，这是专门为特雷西亚控制的位置吗？
```

所以推荐：

```text
训练标注：funasr_large
实时交互：paraformer-zh-streaming + final 标点恢复
```

---

## 5. 本项目与 funasr-back 对比

| 维度 | MonGSV FastAPI | funasr-back |
|------|----------------|-------------|
| 后端框架 | FastAPI + Uvicorn | Django + Daphne |
| 训练 ASR | `paraformer-large + VAD + PUNC` | 无训练链路 |
| 实时 ASR | `/ws/asr/transcribe` | `ws/voice/transcribe/` |
| 实时模型 | `paraformer-zh-streaming` | `paraformer-zh-streaming` |
| 标点恢复 | final 阶段 `ct-punc` | 独立标点模型 |
| 声纹识别 | 支持注册/识别/验证接口 | 支持 |
| TTS 训练/推理 | 支持完整链路 | 不负责 |

---

## 6. 对接建议

music 后端/前端建议这样用：

| 需求 | 调用接口 |
|------|----------|
| 上传音频并训练角色 | `/workflow/training-guide` 或 `/workflow/complete` |
| 单文件转录 | `/inference/transcribe` |
| 实时麦克风识别 | `/ws/asr/transcribe` |
| 训练数据批量 ASR | `/data-prep/asr/recognize` |

前端不要自己决定训练 ASR 模型，只需要传：

```text
world
version
role
language
raw audio
```

后端会按训练流程自动使用 `funasr_large` 完成标注。
