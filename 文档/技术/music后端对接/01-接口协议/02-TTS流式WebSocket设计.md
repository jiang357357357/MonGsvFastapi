# TTS 流式 WebSocket

核对日期：2026-10-24。协议已实现；文末远程结果是历史 V2ProPlus 测试快照，不能代表当前 V5 延迟或官方新增语义流式能力已验收。

目标：支持调用方把长文本或 LLM 流式 delta 发给 GSV，GSV 后端负责缓冲、切句、排队合成，并通过同一个 WebSocket 按顺序返回音频块。

## 1. 接口定位

接口：

```text
ws://host:40302/ws/tts/stream
```

它和现有接口的关系：

| 接口 | 场景 | 返回方式 |
|------|------|----------|
| `POST /api/synthesis/role-emotion` | 一段文本完整合成 | 完整 wav/base64 |
| `POST /inference/tts` | 已知模型与参考音频的完整合成 | 完整 wav/base64 |
| `WS /ws/tts/stream` | LLM delta、长文本、实时对话 | 分段音频 chunk |

当前请求底层 `streaming_mode=true`，实际返回方式按模型区分：

| 模型 | `ready.stream_mode` | 行为 |
|------|---------------------|------|
| V1/V2/V2Pro/V2ProPlus | `tokens` | 旧管线按语义 Token 分块输出 |
| V3/V4/V5dev/V5turbo | `segments` | 底层回退为整段生成后返回；V5 为 48 kHz |

两个 HTTP TTS 接口均返回完整 WAV。WS 的 `start` 不提供官方 `streaming_mode=0/1/2/3` 档位选择。

当前内核基线为官方 `1b47ca0`。本次对照的官方 `b4570b8` 新增 `gpt_streaming`、声学窗口、前瞻、重叠和语义流加速，支持 V2ProPlus/V5dev/V5turbo；这些新参数尚未接入本后端，发送它们不会启用新流式路径。

## 2. 核心原则

1. 调用方只负责发送文本，不负责切句。
2. 后端统一解析 `role + emotion` 到模型路径、参考音频和参考文本。
3. 后端按标点、长度、超时把文本切成适合 TTS 的片段。
4. 单个会话内音频输出必须按 `seq` 顺序返回。
5. 支持停止会话输出；客户端在打断时清空已缓存音频。后台计算取消的限制见下文。
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
  "how_to_cut": "按标点符号切",
  "speed": 1.0,
  "top_k": 15,
  "top_p": 1.0,
  "temperature": 1.0,
  "pause_second": 0.3
}
```

可选高级参数和当前边界：

| 参数 | 默认 / 范围 | 当前行为 |
|------|-------------|----------|
| `sample_steps` | 4、8、16、32 | 不传时 V3=32、V4=8、V5dev=32、V5turbo=4 |
| `cfg_rate` | 0–2 | 不传时 V5dev=1.30，其余默认 0 |
| `pause_second` | 默认 0.3，范围 0.1–0.5 秒 | 映射为 `fragment_interval`；0 会校验失败 |
| `top_k` | 默认 15，范围 1–100 | 0 被旧默认值逻辑替换为 15，调用方应传有效值 |
| `top_p`、`temperature` | 默认 1，范围 0–1 | 当前传入 0 会被替换成 1；需零值时使用 HTTP |
| `seed` | 尚未接入 | WS 不转发此字段，实际使用 -1 随机；固定种子请使用 HTTP |
| `if_freeze` | 默认 false | 兼容保留，未实现上次语义结果冻结 |
| 加速开关 | 固定关闭 | WS 不接收 `inference_mode`，推理时关闭 CUDA Graph 与 FlashAttention |

表中标明的参数限制仍是当前实现问题，不表示代码已经修复。

服务端响应：

```json
{
  "type": "ready",
  "request_id": "chat-001",
  "format": "pcm_s16le",
  "channels": 1,
  "stream_mode": "tokens"
}
```

注意：`ready` 表示角色、情感和模型已准备好；实际采样率在每个 `audio_start` 事件里返回。

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

请求停止当前会话的异步消费与后续输出。客户端收到响应后还需清空播放缓冲。

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

当前取消会取消异步 worker，后台推理线程没有同步停止信号，可能继续占用 GPU。`finish` 会在接收循环内等待输出完成，期间新的 `cancel` 消息也可能要等它完成后才被读取。不要依赖 `cancelled` 判断 GPU 已空闲或立即切换模型。

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
  "seq": 1,
  "sample_rate": 32000,
  "bytes": 175360
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

已新增：

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

`InferenceService` 已增加流式方法：

```python
def stream_inference(self, request: InferenceRequest):
    inputs = self._build_tts_inputs(request, ref_audio_path)
    inputs["streaming_mode"] = True
    inputs["return_fragment"] = False
    inputs["parallel_infer"] = False
    inputs["split_bucket"] = False
    inputs["use_cuda_graph"] = False
    inputs["use_flash_attention"] = False

    for sample_rate, audio in self.tts_pipeline.run(inputs):
        yield sample_rate, audio
```

WebSocket 外层的 `TextSegmenter` 处理 LLM delta 和片段排队。旧 Token 流式适用于 V1/V2/Pro 系列；V3/V4/V5 的底层 `use_vocoder` 分支会关闭流式并打开分段返回。不能仅根据输入中 `streaming_mode=true` 推断模型在段内持续产出音频。

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

当前实现已经复用同一套角色、情感、模型和参考音频解析规则；后续可继续把 HTTP 与 WS 中重复的校验代码抽成公共函数。

## 8. 并发与顺序

单个 WebSocket 会话：

```text
text_delta -> segment_queue -> tts_worker -> audio output
```

默认一个会话只跑一个 `tts_worker`，保证音频顺序自然。

当前实际限制：

| 项目 | 行为 |
|------|------|
| 单连接片段队列 | `asyncio.Queue(maxsize=16)`；满时等待入队 |
| 单连接推理 | 一个异步 worker，按 `seq` 串行消费 |
| 多连接 / HTTP 与 WS | 共用推理实例，没有全局模型互斥与 GPU worker 配额 |
| 文本总长度 | 当前未实现 4000 字硬限制；切句长度是启发式，不能视为请求校验 |

当前不会返回专门的 `queue_full` 事件，也没有已生效的“单 GPU 最多 1–2 worker”限额。调用方应限制输入、消费播放队列，并串行协调模型切换与合成。普通 HTTP 推理还会同步占用事件循环。

## 9. 客户端播放

客户端收到二进制 PCM 后，需要按 `sample_rate/channels/format` 入队播放。

浏览器端建议：

```text
WebSocket binary -> Int16Array -> Float32Array -> AudioContext buffer queue
```

Node/Python 客户端可以直接送播放器或写入 PCM/WAV。

注意：裸 PCM 不能直接给 `<audio>` 标签播放。

## 10. 第一阶段实现范围

第一阶段已完成：

1. 新增 `/ws/tts/stream`
2. 支持 `start/text_delta/text/flush/finish/cancel`
3. 支持 `role_id + emotion`
4. 返回 `pcm_s16le` 二进制 chunk
5. 单连接串行合成
6. 日志打印 `seq/text/audio_bytes/sample_rate`

## 11. 历史验证结果

远程服务：

```text
ws://10.8.0.4:40302/ws/tts/stream
```

测试参数应通过资源接口动态获取：

```json
{
  "request_id": "tts-test-001",
  "role_id": 427041150,
  "emotion": "淡然",
  "version": "v2ProPlus",
  "text_language": "zh"
}
```

上面的 ID 仅代表一次部署快照。调用方必须先请求 `GET /api/role/list/` 和 `GET /api/role/emotions/?role_id=...`，不要长期硬编码角色 ID。

测试文本：

```text
博士，今天也辛苦了。
接下来就交给我吧。
```

一次端到端返回结构示例：

```text
connection
status: 加载角色与模型
ready
audio_start seq=1 sample_rate=32000
binary pcm chunk x3
audio_end seq=1 bytes=175360
audio_start seq=2 sample_rate=32000
binary pcm chunk x3
audio_end seq=2 bytes=198400
end
```

后端日志：

```text
流式推理模式已开启
[WS-TTS] seq=1 text='博士，今天也辛苦了。' bytes=175360 sr=32000
[WS-TTS] seq=2 text='接下来就交给我吧。' bytes=198400 sr=32000
```

底层模式 0/1 对照测试（普拉娜、淡然、143 字长文本、固定 `seed=1234`、预热后）结果：

| 指标 | 模式 0 | 模式 1 |
|------|-------:|-------:|
| 返回块数 | 1 | 11 |
| 首包时间 | 3.552 秒 | 0.512 秒 |
| 总耗时 | 3.677 秒 | 3.733 秒 |
| 音频时长 | 39.50 秒 | 39.54 秒 |

该结果仅为当时 V2ProPlus 底层模式 0/1 的记录，不是当前 V5 性能测试，也不是官方 `gpt_streaming` 的测试。当前 WS 的实际返回方式以 `ready.stream_mode` 和所加载版本为准。

暂不做：

- 多角色并发预加载
- 服务端主动重采样格式选择
- opus/mp3/aac 实时编码
- 多片段乱序并发合成
- 前端浏览器播放器组件

## 12. 后续增强

后续可以增加：

- `voice_profile` 预设，减少每次 start 参数。
- `priority` 和 `interrupt`，支持抢占当前合成。
- `audio_format=wav_chunk/pcm_s16le/base64_pcm`。
- `latency_profile=fast/balanced/quality`。
- 接入官方最新语义流式内核、窗口参数及匹配的加速后端。
- 补齐全局模型互斥、后台线程取消和 WS 采样参数传递。
- 统计首包延迟、片段合成耗时、总音频时长。
