# TTS 流式 WebSocket 设计

目标：支持调用方把长文本或 LLM 流式 delta 发给 GSV，GSV 后端负责缓冲、切句、排队合成，并通过同一个 WebSocket 按顺序返回音频块。

## 1. 接口定位

新增接口：

```text
ws://host:40302/ws/tts/stream
```

它和现有接口的关系：

| 接口 | 场景 | 返回方式 |
|------|------|----------|
| `POST /api/synthesis/role-emotion` | 一段文本完整合成 | 完整 wav/base64 |
| `POST /inference/tts` | 已知模型与参考音频的完整合成 | 完整 wav/base64 |
| `WS /ws/tts/stream` | LLM delta、长文本、实时对话 | 分段音频 chunk |

## 2. 核心原则

1. 调用方只负责发送文本，不负责切句。
2. 后端统一解析 `role + emotion` 到模型路径、参考音频和参考文本。
3. 后端按标点、长度、超时把文本切成适合 TTS 的片段。
4. 单个会话内音频输出必须按 `seq` 顺序返回。
5. 支持取消当前合成，避免用户打断后继续播旧音频。
6. 最终音频优先返回二进制 PCM，降低延迟和编码成本。

## 3. 消息协议

### 3.1 start

建立一次 TTS 会话，加载角色、情感和模型。

```json
{
  "type": "start",
  "request_id": "chat-001",
  "role_id": 1,
  "emotion": "温柔",
  "world_id": 1,
  "version": "v2ProPlus",
  "text_language": "zh",
  "how_to_cut": "不切",
  "speed": 1.0,
  "top_k": 20,
  "top_p": 0.6,
  "temperature": 0.6,
  "sample_steps": 8
}
```

服务端响应：

```json
{
  "type": "ready",
  "request_id": "chat-001",
  "sample_rate": 32000,
  "format": "pcm_s16le",
  "channels": 1
}
```

### 3.2 text_delta

LLM 每吐出一段文本，调用方就发送一次。

```json
{
  "type": "text_delta",
  "request_id": "chat-001",
  "text": "博士，"
}
```

长文本也可以直接拆成多次 `text_delta` 发送，后端会统一缓冲。

### 3.3 text

一次性提交完整文本。后端仍然走同一套分段队列。

```json
{
  "type": "text",
  "request_id": "chat-001",
  "text": "博士，今天也辛苦了。接下来交给我吧。"
}
```

### 3.4 flush

要求后端立刻把当前缓冲区切出一段去合成。

```json
{
  "type": "flush",
  "request_id": "chat-001"
}
```

适用于 LLM 暂停但还没输出句号的情况。

### 3.5 finish

文本输入结束。后端合成剩余缓冲，全部音频发送完后返回 `end`。

```json
{
  "type": "finish",
  "request_id": "chat-001"
}
```

### 3.6 cancel

取消当前请求，停止后续合成和输出。

```json
{
  "type": "cancel",
  "request_id": "chat-001"
}
```

服务端响应：

```json
{
  "type": "cancelled",
  "request_id": "chat-001"
}
```

## 4. 音频返回协议

每个文本片段开始合成前，服务端发送：

```json
{
  "type": "audio_start",
  "request_id": "chat-001",
  "seq": 1,
  "text": "博士，今天也辛苦了。",
  "sample_rate": 32000,
  "format": "pcm_s16le",
  "channels": 1
}
```

随后发送若干二进制帧：

```text
binary pcm_s16le chunk
binary pcm_s16le chunk
...
```

片段结束：

```json
{
  "type": "audio_end",
  "request_id": "chat-001",
  "seq": 1
}
```

整次请求结束：

```json
{
  "type": "end",
  "request_id": "chat-001"
}
```

错误：

```json
{
  "type": "error",
  "request_id": "chat-001",
  "message": "当前角色缺少参考音频"
}
```

## 5. 文本分段策略

后端维护一个 `TextSegmenter`：

```text
buffer += delta
```

满足任一条件就切出一个待合成片段：

| 条件 | 默认值 | 说明 |
|------|--------|------|
| 句末标点 | `。！？!?` | 优先在完整句结束处切 |
| 软标点 | `，；、,;` | 缓冲过长时可在软标点切 |
| 首包最大长度 | 30 字 | 让第一段尽快出声 |
| 后续最大长度 | 80 字 | 平衡自然度和延迟 |
| 最小合成长度 | 6 字 | 避免太碎 |
| 等待超时 | 1000ms | LLM 暂停但没有句号时触发 |
| finish | 强制切出 | 合成剩余文本 |

建议：

- 第一段宁可短一点，降低首包延迟。
- 后续片段稍长，声音更自然。
- 不要按每个 token 合成。
- 不要把省略号、数字、小数点错误拆开。

## 6. 后端内部结构

建议新增：

```text
Code/FastApi/Base/TTS/consumers/stream.py
Code/FastApi/Base/TTS/streaming/session.py
Code/FastApi/Base/TTS/streaming/segmenter.py
Code/FastApi/Base/TTS/streaming/protocol.py
```

职责：

| 模块 | 职责 |
|------|------|
| `stream.py` | WebSocket 收发、连接生命周期 |
| `session.py` | 单个 TTS 会话状态、队列、取消 |
| `segmenter.py` | 文本 delta 缓冲和切句 |
| `protocol.py` | 消息类型、校验、错误响应 |

`InferenceService` 增加一个流式方法：

```python
def stream_inference(self, request: InferenceRequest):
    inputs = self._build_tts_inputs(request, ref_audio_path)
    inputs["streaming_mode"] = True
    inputs["return_fragment"] = False
    inputs["parallel_infer"] = False
    inputs["split_bucket"] = False

    for sample_rate, audio in self.tts_pipeline.run(inputs):
        yield sample_rate, audio
```

WebSocket consumer 负责把 `float32/int16 ndarray` 转成 `pcm_s16le bytes` 后发送。

## 7. 角色与情感解析

`start` 阶段复用现有 `/api/synthesis/role-emotion` 的解析逻辑：

1. `RoleService.get_role(role_id)`
2. 校验 `world_id/version`
3. 查 `role.gpt_model_path / role.sov_model_path`
4. 查 `role_service.list_role_emotions(role_id)`
5. 用 `emotion` 找参考音频 `music_url`
6. 用情感文本或角色 `prompt_text` 作为 `prompt_text`
7. 调 `service.load_models(...)`

这段逻辑后续应抽成公共函数，避免 HTTP 和 WS 各写一份。

## 8. 并发与顺序

单个 WebSocket 会话：

```text
text_delta -> segment_queue -> tts_worker -> audio output
```

默认一个会话只跑一个 `tts_worker`，保证音频顺序自然。

多会话并发由服务层限制：

| 限制 | 建议 |
|------|------|
| 单 GPU 同时 TTS worker | 1-2 |
| 单连接待合成片段队列 | 最多 16 |
| 单片段最大文本长度 | 120 字 |
| 单请求最长文本 | 4000 字 |

队列满时返回：

```json
{
  "type": "error",
  "code": "queue_full",
  "message": "TTS 队列已满，请稍后发送"
}
```

## 9. 客户端播放

客户端收到二进制 PCM 后，需要按 `sample_rate/channels/format` 入队播放。

浏览器端建议：

```text
WebSocket binary -> Int16Array -> Float32Array -> AudioContext buffer queue
```

Node/Python 客户端可以直接送播放器或写入 PCM/WAV。

注意：裸 PCM 不能直接给 `<audio>` 标签播放。

## 10. 第一阶段实现范围

第一阶段只做最小闭环：

1. 新增 `/ws/tts/stream`
2. 支持 `start/text_delta/text/flush/finish/cancel`
3. 支持 `role_id + emotion`
4. 返回 `pcm_s16le` 二进制 chunk
5. 单连接串行合成
6. 日志打印 `request_id/seq/text/audio_bytes/duration`

暂不做：

- 多角色并发预加载
- 服务端主动重采样格式选择
- opus/mp3/aac 实时编码
- 多片段乱序并发合成
- 前端浏览器播放器组件

## 11. 后续增强

后续可以增加：

- `voice_profile` 预设，减少每次 start 参数。
- `priority` 和 `interrupt`，支持抢占当前合成。
- `audio_format=wav_chunk/pcm_s16le/base64_pcm`。
- `latency_profile=fast/balanced/quality`。
- 服务端缓存最近的参考音频特征。
- 统计首包延迟、片段合成耗时、总音频时长。
