# API 完整手册

> 统一网关基础地址：`http://{host}:{port}`，默认 `http://localhost:40302`

## 通用说明

### Content-Type 策略

| 请求类型 | Content-Type | 说明 |
|----------|-------------|------|
| 带文件上传的 POST | `multipart/form-data` | 大多数 API |
| 纯结构体 POST | `application/json` | World/Role 的 CRUD |
| GET 请求 | 无 Body | 参数通过 Query String |

### 认证

默认不启用。启动时加 `--enable-auth --api-key xxx` 后，所有请求需携带：

```http
Authorization: Bearer {api_key}
```

### 响应格式

成功：
```json
{
  "success": true,
  "message": "操作成功描述",
  // ... 各端点特有字段
}
```

失败（HTTP 4xx/5xx）：
```json
{
  "detail": "错误描述"
}
```

---

## 1. 系统服务

### GET /

服务根路径。

**响应示例：**
```json
{
  "service": "GPT-SoVITS 统一网关",
  "version": "2.1.0",
  "status": "running",
  "available_services": ["audio_slice", "asr_recognition", "text_processing", "audio_features", "semantic_encoding", "gpt_training", "sovits_training", "inference"],
  "documentation": "/docs"
}
```

### GET /health

健康检查，返回所有子服务的加载状态。

**响应示例：**
```json
{
  "gateway_status": "healthy",
  "services": {
    "audio_slice": { "status": "available" },
    "asr_recognition": { "status": "available" },
    "gpt_training": { "status": "available" },
    "inference": { "status": "available" }
  },
  "total_services": 8,
  "healthy_services": 8
}
```

### GET /services/status

获取所有服务的详细运行状态。

### POST /services/reload/{service_name}

热重载指定服务。`service_name` 可选值：`audio_slice`, `asr_recognition`, `text_processing`, `audio_features`, `semantic_encoding`, `gpt_training`, `sovits_training`, `inference`

---

## 2. 数据准备

### POST /data-prep/audio-slice/process

长音频智能切分。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input_path` | string | 是 | - | 输入音频文件或目录路径 |
| `output_dir` | string | 是 | - | 输出目录路径 |
| `threshold` | float | 否 | `-34.0` | 切分阈值(dB) |
| `min_length` | int | 否 | `4000` | 最小切片长度(ms) |

**响应示例：**
```json
{
  "success": true,
  "message": "音频切分完成",
  "output_dir": "/output/sliced",
  "processed_files": ["audio1.wav", "audio2.wav"],
  "output_files": ["audio1_slice1.wav", "audio1_slice2.wav"],
  "processing_time": 12.5
}
```

### POST /data-prep/asr/recognize

ASR 语音识别。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_dir` | string | 二选一 | `""` | 音频目录路径 |
| `audio_file` | file | 二选一 | - | 直接上传音频文件 |
| `output_file` | string | 是 | - | 输出标注文件路径(.list) |
| `language` | string | 否 | `"zh"` | 语言 |

**响应示例：**
```json
{
  "success": true,
  "message": "ASR识别完成",
  "output_file": "/output/asr/audio.list",
  "processed_files": ["audio1.wav"],
  "recognition_results": [
    {
      "file": "audio1.wav",
      "text": "今天的天气真好",
      "language": "zh"
    }
  ],
  "processing_time": 3.2
}
```

---

## 3. 数据集格式化

### POST /dataset/text/extract

BERT 文本特征提取。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `list_file` | string | 是 | - | ASR 输出的 .list 文件路径 |
| `input_wav_dir` | string | 是 | - | 切片音频目录 |
| `experiment_name` | string | 否 | `"default"` | 实验名称 |
| `output_dir` | string | 是 | - | 输出目录 |

### POST /dataset/audio/extract

SoVITS 音频特征提取。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `list_file` | string | 是 | - | .list 文件路径 |
| `input_wav_dir` | string | 是 | - | 音频目录 |
| `experiment_name` | string | 否 | `"default"` | 实验名称 |
| `output_dir` | string | 是 | - | 输出目录 |
| `version` | string | 否 | `"v2Pro"` | 模型版本 |

### POST /dataset/semantic/encode

CNHuBERT 语义编码。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `list_file` | string | 是 | - | .list 文件路径 |
| `cnhubert_dir` | string | 否 | `""` | CNHuBERT 特征目录 |
| `experiment_name` | string | 否 | `"default"` | 实验名称 |
| `output_dir` | string | 是 | - | 输出目录 |
| `version` | string | 否 | `"v2Pro"` | 模型版本 |

---

## 4. 模型训练

### POST /training/gpt/start

启动 GPT 训练。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `exp_name` | string | 是 | - | 实验名称 |
| `exp_root` | string | 二选一 | `""` | 实验根目录 |
| `workspace_dir` | string | 二选一 | `""` | 工作区目录（与 exp_root 二选一） |
| `model_output_dir` | string | 否 | `""` | 模型输出目录 |
| `version` | string | 否 | `"v2Pro"` | 模型版本 |
| `batch_size` | int | 否 | `8` | 批次大小 |
| `total_epoch` | int | 否 | `15` | 总训练轮数 |

**响应示例：**
```json
{
  "success": true,
  "message": "GPT训练已启动",
  "job_id": "gpt_20260522_123456",
  "exp_name": "my_project",
  "status": "running",
  "config_file": "/output/train/config.yaml",
  "log_dir": "/output/train/logs",
  "model_dir": "/output/train/models"
}
```

### POST /training/sovits/start

启动 SoVITS 训练。参数与 GPT 训练类似，区别是默认 `batch_size=32`、`total_epoch=8`。

### GET /training/status/{job_id}

查询训练状态。

**响应示例：**
```json
{
  "type": "gpt",
  "status": {
    "job_id": "gpt_20260522_123456",
    "status": "running",
    "progress": 45.0,
    "current_epoch": 7,
    "total_epochs": 15,
    "start_time": "2026-05-22T12:00:00",
    "elapsed_time": 1234.5,
    "eta": 1500.0
  }
}
```

状态值：`running` / `completed` / `failed` / `stopped`

### POST /training/stop/{job_id}

停止训练任务。

---

## 5. TTS 推理

### POST /api/synthesis/role-emotion

按角色与情感合成语音。**这是前端和 music 后端推荐使用的业务接口**。

调用方只提交业务选择：世界、版本、角色、情感和文本。后端负责查找角色模型路径、情感参考音频、参考文本，自动加载 GPT/SoVITS 模型，然后执行底层推理。

**请求参数（application/json）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `role_id` | int | **是** | - | 角色 ID |
| `emotion` | string | **是** | - | 情感名称，需存在于该角色的情感配置中 |
| `text` | string | **是** | - | 要合成的文本 |
| `text_language` | string | 否 | `"zh"` | 目标文本语言 |
| `world_id` | int | 否 | `null` | 世界 ID；传入时后端会校验角色是否属于该世界 |
| `version` | string | 否 | `null` | 版本；传入时后端会校验角色是否属于该版本 |
| `how_to_cut` | string | 否 | `"凑四句一切"` | 文本切分方式 |
| `top_k` | int | 否 | `20` | Top-K 采样 |
| `top_p` | float | 否 | `0.6` | Top-P 采样 |
| `temperature` | float | 否 | `0.6` | 温度参数 |
| `speed` | float | 否 | `1.0` | 语速 |
| `sample_steps` | int | 否 | `8` | 采样步数 |
| `if_sr` | bool | 否 | `false` | 启用音频超分 |
| `ref_free` | bool | 否 | `false` | 无参考模式 |
| `if_freeze` | bool | 否 | `false` | 冻结缓存 |
| `pause_second` | float | 否 | `0.3` | 句间停顿(秒) |
| `use_cuda_graph` | bool | 否 | `false` | 尝试使用 CUDA Graph 加速普通非流式推理；仅 CUDA、单条普通推理时启用，失败会自动回退 |
| `return_base64` | bool | 否 | `true` | 返回 base64 音频 |

**后端内部解析规则：**

| 来源 | 字段 | 用途 |
|------|------|------|
| 角色 `GET /api/role/list/` | `gpt_model_path` | 自动加载 GPT 模型 |
| 角色 `GET /api/role/list/` | `sov_model_path` | 自动加载 SoVITS 模型 |
| 情感 `GET /api/role/emotions/` | `music_url` | 作为底层推理的 `ref_audio_path` |
| 情感 `GET /api/role/emotions/` | `text` | 作为底层推理的 `prompt_text` |
| 情感 `GET /api/role/emotions/` | `text_language` | 作为底层推理的 `prompt_language` |

**请求示例：**
```json
{
  "world_id": 1,
  "version": "v2Pro",
  "role_id": 1,
  "emotion": "温柔",
  "text": "博士，今天也辛苦了。",
  "text_language": "zh",
  "speed": 1.0,
  "how_to_cut": "凑四句一切",
  "use_cuda_graph": false
}
```

**响应示例（return_base64=true）：**
```json
{
  "success": true,
  "message": "推理完成",
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQ...",
  "sample_rate": 32000,
  "duration": 3.5,
  "processing_time": 1.23,
  "text_segments": ["博士，今天也辛苦了。"]
}
```

**常见错误：**

| 状态码 | detail | 说明 |
|--------|--------|------|
| `400` | `当前角色缺少 GPT 或 SoVITS 模型路径` | 角色没有可用模型 |
| `400` | `当前角色没有情感配置: xxx` | 情感名称不存在 |
| `400` | `当前情感缺少参考音频` | 情感配置没有可用参考音频 |
| `400` | `模型加载失败` | 模型路径无效或权重加载失败 |

### POST /inference/models/load

加载推理模型。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `gpt_path` | string | 是 | GPT 模型权重路径 |
| `sovits_path` | string | 是 | SoVITS 模型权重路径 |

路径示例：
- `GPT_weights_v2Pro/my_role.ckpt`
- `SoVITS_weights_v2Pro/my_role.pth`
- `GPT_SoVITS/pretrained_models/s1v3.ckpt`（底模）

**响应示例：**
```json
{
  "success": true,
  "message": "模型加载成功",
  "gpt_path": "GPT_weights_v2Pro/my_role.ckpt",
  "sovits_path": "SoVITS_weights_v2Pro/my_role.pth"
}
```

### POST /inference/tts

文本转语音推理。**这是底层接口**，不会自动根据角色或情感查找参考音频，也不会自动选择角色模型。业务对接优先使用 `POST /api/synthesis/role-emotion`。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | **是** | - | 要合成的文本 |
| `text_language` | string | 否 | `"zh"` | 文本语言 |
| `ref_audio` | file | 二选一 | - | 上传参考音频文件 |
| `ref_audio_path` | string | 二选一 | `""` | 参考音频路径 |
| `prompt_text` | string | 否 | `""` | 参考文本 |
| `prompt_language` | string | 否 | `"zh"` | 参考文本语言 |
| `how_to_cut` | string | 否 | `"凑四句一切"` | 文本切分方式 |
| `top_k` | int | 否 | `20` | Top-K 采样 |
| `top_p` | float | 否 | `0.6` | Top-P 采样 |
| `temperature` | float | 否 | `0.6` | 温度参数 |
| `speed` | float | 否 | `1.0` | 语速 |
| `sample_steps` | int | 否 | `8` | 采样步数 |
| `if_sr` | bool | 否 | `false` | 启用音频超分 |
| `ref_free` | bool | 否 | `false` | 无参考模式 |
| `if_freeze` | bool | 否 | `false` | 冻结缓存 |
| `pause_second` | float | 否 | `0.3` | 句间停顿(秒) |
| `use_cuda_graph` | bool | 否 | `false` | 尝试使用 CUDA Graph 加速普通非流式推理；仅 CUDA、单条普通推理时启用，失败会自动回退 |
| `return_base64` | bool | 否 | `true` | 返回 base64 音频 |

**how_to_cut 可选值：**
- `"不切"` / `"cut0"` — 不切分
- `"凑四句一切"` / `"cut1"` — 每四句一切（默认）
- `"凑50字一切"` / `"cut2"` — 每50字一切
- `"按中文句号。切"` / `"cut3"` — 按句号切
- `"按英文句号.切"` / `"cut4"` — 按英文句号切
- `"按标点符号切"` / `"cut5"` — 按标点切

**text_language 可选值：**
`auto`, `auto_yue`, `zh`, `en`, `ja`, `yue`, `ko`, `all_zh`, `all_ja`, `all_yue`, `all_ko`

**CUDA Graph 说明：**

`use_cuda_graph=true` 只影响 T2S 语义 token 预测阶段。当前实现为安全可选能力：只有在 `cuda + 非 streaming + 非 ref_free + 单条普通推理` 时尝试启用；初始化或推理失败时后端会输出 `[cuda-graph]` 日志并自动回退普通推理。

**响应示例（return_base64=true）：**
```json
{
  "success": true,
  "message": "推理完成",
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQ...",
  "sample_rate": 32000,
  "duration": 3.5,
  "processing_time": 1.23,
  "text_segments": ["你好，欢迎使用语音合成系统。"],
  "model_info": {
    "gpt_path": "GPT_weights_v2Pro/my_role.ckpt",
    "sovits_path": "SoVITS_weights_v2Pro/my_role.pth",
    "model_version": "v2Pro",
    "device": "cuda",
    "is_half": true,
    "models_loaded": true
  }
}
```

**响应示例（return_base64=false）：**
```json
{
  "success": true,
  "message": "推理完成",
  "audio_path": "/tmp/gpt_sovits_infer_xxxxx.wav",
  "sample_rate": 32000,
  "duration": 3.5,
  "processing_time": 1.23,
  "text_segments": ["你好，欢迎使用语音合成系统。"]
}
```

### GET /inference/models/info

获取当前已加载模型信息。

**响应示例：**
```json
{
  "gpt_path": "GPT_weights_v2Pro/my_role.ckpt",
  "sovits_path": "SoVITS_weights_v2Pro/my_role.pth",
  "model_version": "v2Pro",
  "device": "cuda:0",
  "is_half": true,
  "models_loaded": true,
  "supported_languages": ["auto", "zh", "en", "ja"],
  "residency": {
    "loaded_models": 1,
    "active_requests": 0,
    "idle_ttl_seconds": 1200
  }
}
```

### POST /inference/models/unload

卸载当前推理模型，释放显存。

### POST /inference/models/cleanup

执行模型驻留清理。可选参数 `force`（form-data，默认 `false`）。

### GET /inference/ref-audio?path=...

获取参考音频文件，供前端播放试听。返回音频文件流。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | Query String，音频文件路径 |

支持格式：`.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`, `.aac`

---

## 6. ASR 转录（轻量接口）

### ASR 使用原则

ASR 分为训练标注和实时识别两条链路：

| 场景 | 推荐接口 | 使用模型 |
|------|----------|----------|
| 训练数据准备 | `/data-prep/asr/recognize` 或工作流接口 | `funasr_large`，即 `paraformer-large + VAD + ct-punc` |
| 单文件转录 | `/inference/transcribe` | 默认 `funasr` |
| 实时语音输入 | `/ws/asr/transcribe` | `paraformer-zh-streaming`，final 阶段补标点 |

训练标注不要使用 streaming 模型。训练流程默认会走离线 FunASR large，并输出带标点的 `.list` 文件。

### POST /inference/transcribe

单文件语音转录，面向前端设计，返回文字而非文件。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_file` | file | 二选一 | - | 上传音频 |
| `audio_path` | string | 二选一 | `""` | 音频路径 |
| `language` | string | 否 | `"zh"` | 语言 |
| `model_type` | string | 否 | `"funasr"` | ASR 模型类型 |
| `model_size` | string | 否 | `"large"` | 模型大小 |
| `precision` | string | 否 | `"float32"` | 精度 |

**响应示例：**
```json
{
  "success": true,
  "message": "ASR识别完成",
  "text": "今天的天气真好，适合出门散步。",
  "language": "zh",
  "segments": [
    { "text": "今天的天气真好", "start": 0.0, "end": 2.1, "language": "zh" },
    { "text": "适合出门散步", "start": 2.1, "end": 3.8, "language": "zh" }
  ],
  "processing_time": 1.5
}
```

### POST /inference/transcribe/models/load

预加载 ASR 模型。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model_type` | string | 否 | `"funasr"` | 模型类型 |
| `model_size` | string | 否 | `"large"` | 模型大小 |
| `language` | string | 否 | `"zh"` | 语言 |
| `precision` | string | 否 | `"float32"` | 精度 |

### GET /inference/transcribe/models/info

获取当前 ASR 模型信息。

### POST /inference/transcribe/models/unload

卸载 ASR 模型。

### POST /inference/transcribe/models/cleanup

ASR 驻留清理。

### WebSocket /ws/asr/transcribe

实时语音识别接口，面向前端麦克风或 music 后端实时语音输入。

连接地址：

```text
ws://host:40302/ws/asr/transcribe
```

连接成功后，服务端会立即返回 `type=connection` 的 JSON 消息。该路由不做 token 鉴权，也不限制 Origin。

音频输入必须是裸 PCM 二进制：

| 项 | 要求 |
|----|------|
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

连接成功响应：

```json
{
  "type": "connection",
  "status": "connected",
  "message": "2-pass 流式识别已就绪"
}
```

实时片段响应：

```json
{
  "type": "result",
  "text": "实时识别文本",
  "accumulated": "实时识别文本",
  "is_interim": true,
  "sentence_end": false
}
```

最终段落响应：

```json
{
  "type": "result",
  "text": "最终识别文本，带标点。",
  "accumulated": "累计最终文本，带标点。",
  "is_interim": false,
  "sentence_end": true,
  "speaker_id": null,
  "speaker_name": null,
  "speaker_similarity": null,
  "speaker_is_known": null
}
```

停止响应：

```json
{
  "type": "status",
  "message": "录音结束",
  "final_text": "完整最终文本，带标点。"
}
```

**握手排查：**

| 现象 | 优先检查 |
|------|----------|
| WebSocket 握手返回 `403 Forbidden`，HTTP GET 同路径返回 `404` | 后端是否已部署包含 `websocket: WebSocket` 类型标注的版本；PM2 是否跑的是 `Code/FastApi/Main/run_gateway.py start --host 0.0.0.0 --port 40302 --no-reload`；前置代理是否转发 `Upgrade` |
| 连接成功但没有识别结果 | 是否发送了 `{"command":"start"}`；音频是否为 `16kHz/mono/signed int16/little-endian` 裸 PCM |

注意：不要向该接口发送 mp3/wav/m4a 文件块。浏览器或后端调用方需要先解码并转成 `16k mono int16 PCM`。

---

## 7. 工作流（一键式）

### POST /workflow/complete

完整预处理工作流。内部按顺序执行：
1. 音频切片（audio_slice）
2. ASR 识别（asr_recognition）
3. 文本特征提取（text_processing）
4. 音频特征提取（audio_features）
5. 语义编码（semantic_encoding）
6. 【可选】启动 GPT + SoVITS 训练

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `project_name` | string | 是 | - | 项目名称 |
| `input_audio_dir` | string | 是 | - | 原始音频目录 |
| `output_dir` | string | 是 | - | 输出目录 |
| `language` | string | 否 | `"zh"` | 语言 |
| `version` | string | 否 | `"v2Pro"` | 模型版本 |
| `world_name` | string | 否 | `"Standalone"` | 所属世界 |
| `start_training` | bool | 否 | `false` | 完成后是否启动训练 |
| `train_gpt` | bool | 否 | `true` | 训练 GPT |
| `train_sovits` | bool | 否 | `true` | 训练 SoVITS |
| `gpt_batch_size` | int | 否 | `8` | GPT 批次大小 |
| `gpt_total_epoch` | int | 否 | `15` | GPT 训练轮数 |
| `sovits_batch_size` | int | 否 | `32` | SoVITS 批次大小 |
| `sovits_total_epoch` | int | 否 | `8` | SoVITS 训练轮数 |
| `training_order` | string | 否 | `"sovits_first"` | 训练顺序 |

**training_order 可选值：** `"sovits_first"` / `"gpt_first"`

**响应结构：**
```json
{
  "success": true,
  "message": "完整工作流执行完成",
  "project_name": "my_project",
  "project_root": "/output/my_project",
  "steps": [
    { "step": "audio_slice", "result": { ... } },
    { "step": "model_slice_sync", "result": { ... } },
    { "step": "asr_recognition", "result": { ... } },
    { "step": "text_processing", "result": { ... } },
    { "step": "audio_features", "result": { ... } },
    { "step": "semantic_encoding", "result": { ... } }
  ],
  "training_started": false,
  "next_action": "可以开始训练模型"
}
```

### POST /workflow/training/full

预处理 + 训练引导工作流。在 `/workflow/complete` 的基础上，支持直接上传音频文件。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_files` | file[] | 否 | - | 直接上传多个音频文件 |

其他参数与 `/workflow/complete` 相同，`start_training` 固定为 `true`。

### POST /batch/projects

批量处理多个项目。

**请求参数（application/json）：**
```json
{
  "projects": [
    {
      "name": "project_a",
      "input_dir": "/audio/project_a",
      "output_dir": "/output/project_a",
      "language": "zh",
      "version": "v2Pro"
    },
    {
      "name": "project_b",
      "input_dir": "/audio/project_b",
      "output_dir": "/output/project_b",
      "language": "zh",
      "version": "v2Pro"
    }
  ]
}
```

---

## 8. 资源管理

### 8.1 World（世界/逻辑分组）

#### GET /api/world/list/?version=...

列出所有世界。可选过滤 `version`。

**响应示例：**
```json
{
  "version": null,
  "worlds": [
    { "id": 1, "name": "Standalone", "description": "", "created_at": "..." },
    { "id": 2, "name": "我的世界", "description": "角色分组", "created_at": "..." }
  ],
  "count": 2
}
```

#### POST /api/world/create/

**请求参数（application/json）：**
```json
{
  "name": "我的世界",
  "description": "可选描述"
}
```

**响应：**
```json
{
  "message": "世界创建成功",
  "data": { "id": 3, "name": "我的世界" }
}
```

#### POST /api/world/delete/

```json
{
  "id": 3
}
```

### 8.2 Role（角色/音色模型）

#### GET /api/role/list/

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 否 | 按版本过滤 |
| `world_id` | int | 否 | 按世界 ID 过滤 |
| `world_name` | string | 否 | 按世界名过滤 |

**响应示例：**
```json
{
  "success": true,
  "message": "ok",
  "world_id": null,
  "world_name": null,
  "roles": [
    {
      "id": 1,
      "name": "小明",
      "description": "",
      "world_id": 1,
      "world_name": "Standalone",
      "version": "v2Pro",
      "gpt_model_id": null,
      "gpt_model_name": "my_role.ckpt",
      "gpt_model_path": "D:/code/model/mongsvfastapi/Resources/Model/Standalone/小明/v2Pro/GPT/my_role.ckpt",
      "sov_model_id": null,
      "sov_model_name": "my_role.pth",
      "sov_model_path": "D:/code/model/mongsvfastapi/Resources/Model/Standalone/小明/v2Pro/SoVITS/my_role.pth",
      "prompt_text": "参考文本",
      "prompt_audio_path": "D:/code/model/mongsvfastapi/Resources/Model/Standalone/小明/v2Pro/emotion/温柔__zh__参考文本.wav",
      "language": "zh"
    }
  ],
  "count": 1
}
```

`gpt_model_path` 和 `sov_model_path` 是后端业务合成接口自动加载模型时使用的字段。普通前端不需要直接使用这两个字段，除非在测试页或高级模式直接调用 `/inference/models/load`。

#### POST /api/role/create/

**请求参数（application/json）：**
```json
{
  "name": "小明",
  "description": "可选描述",
  "world_id": 1,
  "version": "v2Pro",
  "gpt_model_id": null,
  "sov_model_id": null,
  "prompt_text": "参考文本",
  "prompt_audio_path": "/path/to/ref.wav",
  "language": "zh"
}
```

#### POST /api/role/import/

角色导入，上传 GPT/SoVITS 权重文件。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 角色名 |
| `description` | string | 否 | 描述 |
| `world_id` | int | 否 | 所属世界 |
| `world_name` | string | 否 | 所属世界名 |
| `version` | string | 否 | 版本 |
| `prompt_text` | string | 否 | 参考文本 |
| `language` | string | 否 | 语言 |
| `gpt_file` | file | **是** | GPT 权重文件(.ckpt) |
| `sov_file` | file | **是** | SoVITS 权重文件(.pth) |
| `prompt_audio` | file | 否 | 参考音频文件 |

#### POST /api/role/update/

**请求参数（application/json）：**
```json
{
  "id": 1,
  "name": "小明",
  "world_id": 1,
  "version": "v2Pro",
  "gpt_model_id": 5,
  "sov_model_id": 3
}
```

#### POST /api/role/delete/

```json
{
  "id": 1
}
```

#### 情感配置

**GET /api/role/emotions/?role_id=1** — 列出角色情感配置

**响应示例：**
```json
{
  "success": true,
  "message": "ok",
  "role_id": 1,
  "emotions": [
    {
      "name": "温柔",
      "text": "博士，今天也辛苦了。",
      "music_url": "D:/code/model/mongsvfastapi/Resources/Model/Standalone/小明/v2Pro/emotion/温柔__zh__博士，今天也辛苦了.wav",
      "text_language": "zh",
      "file_name": "温柔__zh__博士，今天也辛苦了.wav"
    }
  ],
  "count": 1
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `name` | 情感名称 |
| `text` | 参考音频对应文本，会作为业务合成时的 `prompt_text` |
| `music_url` | 情感参考音频路径，会作为业务合成时的 `ref_audio_path` |
| `text_language` | 参考文本语言，会作为业务合成时的 `prompt_language` |
| `file_name` | 情感音频文件名 |

**POST /api/role/emotions/upsert/** — 创建或更新情感配置（form-data）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `role_id` | int | 是 | 角色 ID |
| `emotion_name` | string | 是 | 情感名称（如 "开心", "悲伤"） |
| `emotion_text` | string | 是 | 情感对应的参考文本 |
| `text_language` | string | 否 | 文本语言 |
| `audio_file` | file | 否 | 情感参考音频 |
| `audio_source_path` | string | 否 | 音频源路径 |

**POST /api/role/emotions/delete/** — 删除情感配置（form-data）

| 参数 | 类型 | 必填 |
|------|------|------|
| `role_id` | int | 是 |
| `emotion_name` | string | 是 |

#### 角色工作区

**POST /api/role/workspace/create/** — 创建工作区（JSON）

**GET /api/role/workspace/list/** — 列出工作区

**POST /api/role/workspace/upload-audio/** — 上传训练音频（form-data）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `role_name` | string | 是 | 角色名 |
| `target` | string | 否 | `"raw"`（原始）或 `"prompt"`（参考） |
| `create_if_missing` | bool | 否 | `true` |
| `files` | file[] | 是 | 音频文件列表 |

**POST /api/role/workspace/initialize/** — 初始化完整工作区（form-data）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `role_name` | string | 是 | 角色名 |
| `description` | string | 否 | 描述 |
| `world_name` | string | 否 | 世界名 |
| `language` | string | 否 | 语言 |
| `version` | string | 否 | 版本 |
| `base_version` | string | 否 | 基座模型版本 |
| `experiment_name` | string | 否 | 实验名 |
| `overwrite` | bool | 否 | 是否覆写 |
| `raw_files` | file[] | 否 | 原始训练音频 |
| `prompt_files` | file[] | 否 | 参考音频 |

### 8.3 Model（模型权重）

#### GET /api/gpt/list/

列出所有可用的 GPT 权重文件。

**响应示例：**
```json
{
  "message": "获取 GPT 模型列表成功",
  "models": [
    {
      "name": "GPT_weights_v2Pro/my_role.ckpt",
      "version": "v2Pro",
      "path": "GPT_weights_v2Pro/my_role.ckpt"
    },
    {
      "name": "GPT_SoVITS/pretrained_models/s1v3.ckpt",
      "version": "v3"
    }
  ],
  "count": 2
}
```

#### GET /api/sov/list/

列出所有可用的 SoVITS 权重文件，格式同上。

### 8.4 Version（版本）

#### GET /api/models/versions/from-enum/

返回内置的版本枚举列表。

**响应示例：**
```json
{
  "success": true,
  "versions": ["v1", "v2", "v3", "v4", "v2Pro", "v2ProPlus"],
  "count": 6
}
```

#### GET /api/models/versions/from-dir/

从权重目录扫描实际存在的版本。

---

## 附录：支持的模型版本

| 版本标识 | 说明 | 底模 GPT | 底模 SoVITS |
|----------|------|----------|-------------|
| `v1` | 原始版本 | s1bert25hz-2kh-longer | s2G488k.pth |
| `v2` | 第二代 | s1bert25hz-5kh-longer | s2G2333k.pth |
| `v3` | 第三代 | s1v3.ckpt | s2Gv3.pth |
| `v4` | 第四代 | s1v3.ckpt | s2Gv4.pth |
| `v2Pro` | v2 增强版（推荐） | s1v3.ckpt | s2Gv2Pro.pth |
| `v2ProPlus` | v2Pro 升级版 | s1v3.ckpt | s2Gv2ProPlus.pth |
