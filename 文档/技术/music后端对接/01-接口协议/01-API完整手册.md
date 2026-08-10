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
| `output_file` | string | 是 | - | 输出位置提示；传入 `.list` 路径时当前实现只使用其父目录，实际文件名以响应中的 `output_file` 为准 |
| `language` | string | 否 | `"zh"` | 语言 |

**响应示例：**
```json
{
  "success": true,
  "message": "识别完成",
  "output_file": "/output/asr/sliced.list",
  "processed_files": ["/data/audio/sliced/audio1.wav"],
  "recognition_results": [
    {
      "audio_path": "/data/audio/sliced/audio1.wav",
      "speaker": "sliced",
      "language": "ZH",
      "text": "今天的天气真好。"
    }
  ],
  "error_files": [],
  "total_duration": 0.0,
  "processing_time": 3.2
}
```

识别结果中的 `speaker` 目前取输入文件或目录名；`language` 使用大写语言代码。`total_duration` 字段当前保留但尚未统计，通常为 `0.0`。

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
| `how_to_cut` | string | 否 | `"按标点符号切"` | 文本切分方式 |
| `top_k` | int | 否 | `15` | Top-K 采样 |
| `top_p` | float | 否 | `1.0` | Top-P 采样 |
| `temperature` | float | 否 | `1.0` | 温度参数 |
| `speed` | float | 否 | `1.0` | 语速 |
| `sample_steps` | int | 否 | `32` | 采样步数 |
| `if_sr` | bool | 否 | `false` | 启用音频超分 |
| `ref_free` | bool | 否 | `false` | 无参考模式 |
| `if_freeze` | bool | 否 | `false` | 兼容保留字段；当前新推理管线尚未实现冻结缓存 |
| `pause_second` | float | 否 | `0.3` | 句间停顿（秒），当前已接入官方 `fragment_interval` |
| `inference_mode` | string | 否 | `"normal"` | 推理模式：`normal` 普通推理，`accelerated` 加速推理 |
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
  "how_to_cut": "按标点符号切",
  "inference_mode": "normal"
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

### WebSocket /ws/tts/stream

流式文本转语音。适合 LLM delta、长文本和实时对话场景。调用方发送文本流，后端按标点、长度和 flush/finish 切成 TTS 片段，并按顺序返回音频块。

当前 WebSocket 固定调用底层 `streaming_mode=true`、`return_fragment=false`，对应官方模式 2（语义 Token 分块流式）。它不是官方模式 1，客户端目前也不能在 `start` 消息中选择模式 0/1/2/3。

| 官方模式 | 当前外部入口 | 状态 |
|---------:|--------------|------|
| 0 | `POST /api/synthesis/role-emotion`、`POST /inference/tts` | 已开放，完整音频一次返回 |
| 1 | 无 | 底层已验证可用，对外接口尚未开放 |
| 2 | `WS /ws/tts/stream` | 已开放，PCM 分块返回 |
| 3 | 无 | 底层官方支持，对外接口尚未开放 |

**连接地址：**

```text
ws://host:40302/ws/tts/stream
```

**start：**

```json
{
  "type": "start",
  "request_id": "chat-001",
  "role_id": 1,
  "emotion": "温柔",
  "world_id": 1,
  "version": "v2ProPlus",
  "text_language": "zh",
  "speed": 1.0
}
```

**文本输入：**

```json
{"type":"text_delta","request_id":"chat-001","text":"博士，"}
{"type":"text_delta","request_id":"chat-001","text":"今天也辛苦了。"}
{"type":"finish","request_id":"chat-001"}
```

**服务端事件：**

```json
{"type":"ready","request_id":"chat-001","format":"pcm_s16le","channels":1}
{"type":"audio_start","request_id":"chat-001","seq":1,"text":"博士，今天也辛苦了。","sample_rate":32000,"format":"pcm_s16le","channels":1}
```

`ready` 表示模型已准备好；实际采样率以 `audio_start.sample_rate` 为准。`audio_start` 后会发送若干二进制音频帧，格式为 `pcm_s16le / mono`。片段结束：

```json
{"type":"audio_end","request_id":"chat-001","seq":1,"sample_rate":32000,"bytes":123456}
{"type":"end","request_id":"chat-001"}
```

取消：

```json
{"type":"cancel","request_id":"chat-001"}
```

客户端不能把裸 PCM 直接交给 `<audio>` 标签，需要按 `sample_rate/channels/format` 放入播放器队列。

**已验证：**

远程 `10.8.0.4:40302` 已通过端到端测试。`role_id` 由角色目录计算，部署内容变化后可能改变，测试前必须通过 `GET /api/role/list/` 动态获取，不要在调用方硬编码文档中的历史 ID。

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
| `how_to_cut` | string | 否 | `"按标点符号切"` | 文本切分方式 |
| `top_k` | int | 否 | `15` | Top-K 采样 |
| `top_p` | float | 否 | `1.0` | Top-P 采样 |
| `temperature` | float | 否 | `1.0` | 温度参数 |
| `speed` | float | 否 | `1.0` | 语速 |
| `sample_steps` | int | 否 | `32` | 采样步数 |
| `if_sr` | bool | 否 | `false` | 启用音频超分 |
| `ref_free` | bool | 否 | `false` | 无参考模式 |
| `if_freeze` | bool | 否 | `false` | 兼容保留字段；当前新推理管线尚未实现冻结缓存 |
| `pause_second` | float | 否 | `0.3` | 句间停顿（秒），当前已接入官方 `fragment_interval` |
| `inference_mode` | string | 否 | `"normal"` | 推理模式：`normal` 普通推理，`accelerated` 加速推理 |
| `return_base64` | bool | 否 | `true` | 返回 base64 音频 |

**how_to_cut 可选值：**
- `"不切"` / `"cut0"` — 不切分
- `"凑四句一切"` / `"cut1"` — 每四句一切
- `"凑50字一切"` / `"cut2"` — 每50字一切
- `"按中文句号。切"` / `"cut3"` — 按句号切
- `"按英文句号.切"` / `"cut4"` — 按英文句号切
- `"按标点符号切"` / `"cut5"` — 按标点切（默认）

**text_language 可选值：**
`auto`, `auto_yue`, `zh`, `en`, `ja`, `yue`, `ko`, `all_zh`, `all_ja`, `all_yue`, `all_ko`

**推理模式说明：**

`inference_mode=normal` 使用普通推理，是默认值。`inference_mode=accelerated` 会尝试使用 CUDA Graph 加速 T2S 语义 token 预测阶段，仅建议在 CUDA 服务端、非 streaming、非 ref_free、单条普通推理时启用；初始化或推理失败时后端会输出 `[cuda-graph]` 日志并自动回退普通推理。

旧字段 `use_cuda_graph` 和 `cuda_graph_mode` 已废弃，不再作为外部接口参数使用。

这里的 `inference_mode` 只表示普通推理或 CUDA Graph 加速，与官方流式档位 `streaming_mode=0/1/2/3` 不是同一个参数。当前两个 HTTP 接口均按模式 0 返回完整结果。

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
| 中文训练数据准备 | `/data-prep/asr/recognize` 或工作流接口 | FunASR `paraformer-large + FSMN VAD + ct-punc` |
| 粤语训练数据准备 | `/data-prep/asr/recognize` 或工作流接口 | FunASR `UniASR 2-pass Cantonese` |
| 英语、日语、韩语等训练数据准备 | `/data-prep/asr/recognize` 或工作流接口 | Faster-Whisper `large-v3` |
| 单文件转录 | `/inference/transcribe` | 声纹验证通过后使用默认 `funasr` |
| 普通实时语音输入 | `/ws/asr/final` | VAD 断句后调用 final ASR，不要求声纹 |
| 声纹实时语音输入（推荐个人模式） | `/ws/asr/final/voiceprint` | VAD 断句、声纹验证通过后调用 final ASR |
| 旧实时入口 | `/ws/asr/transcribe` | 严格声纹门禁下不再返回 interim，仅返回验证后的 final |

训练标注不要使用 streaming 模型。训练工作流按 `language` 自动分流：`zh`、`yue` 使用 FunASR，其他支持语言使用 Faster-Whisper，并输出 `.list` 文件。

### POST /inference/transcribe

单文件语音转录，面向前端设计，返回文字而非文件。

**请求参数（form-data）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_file` | file | 二选一 | - | 上传音频 |
| `audio_path` | string | 二选一 | `""` | 服务端音频路径；当前只允许 `Resources/Model` 目录内的文件 |
| `speaker_id` | string | 是 | - | 当前登录用户 ID，必须已经通过声纹注册接口登记 |
| `language` | string | 否 | `"zh"` | 语言 |
| `model_type` | string | 否 | `"funasr"` | ASR 模型类型 |
| `model_size` | string | 否 | `"large"` | 模型大小；当前会参与配置校验和驻留键，但尚未传入底层批量识别 |
| `precision` | string | 否 | `"float32"` | 精度；当前会参与配置校验和驻留键，但尚未传入底层批量识别 |

当前真正生效的是 `model_type` 与 `language`。Faster-Whisper 批量识别底层实际仍使用 `large-v3 + float16 + beam_size=5 + VAD`；接口模型中的 `batch_size`、`beam_size`、`vad_filter` 也尚未继续传到底层执行。

**响应示例：**
```json
{
  "success": true,
  "message": "识别完成",
  "text": "今天的天气真好，适合出门散步。",
  "language": "ZH",
  "segments": [
    {
      "audio_path": "/tmp/transcribe_upload_xxx/speech.wav",
      "speaker": "speech.wav",
      "language": "ZH",
      "text": "今天的天气真好，适合出门散步。"
    }
  ],
  "processing_time": 1.5
}
```

`segments` 当前是逐文件识别记录，不包含 `start`、`end` 时间戳。上传文件使用临时路径，响应返回后该临时文件会被删除，不应把 `audio_path` 当作可长期访问的资源地址。

### POST /inference/transcribe/models/load

准备 ASR 引擎并登记驻留状态。当前实现采用延迟加载：Paraformer 或 Whisper 的大模型权重仍在第一次实际识别时加载，因此该接口成功不代表大模型已经完成显存预热。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model_type` | string | 否 | `"funasr"` | 模型类型 |
| `model_size` | string | 否 | `"large"` | 模型大小；当前仅参与校验和驻留键 |
| `language` | string | 否 | `"zh"` | 语言 |
| `precision` | string | 否 | `"float32"` | 精度；当前仅参与校验和驻留键 |

### GET /inference/transcribe/models/info

获取当前 ASR 模型信息。

### POST /inference/transcribe/models/unload

卸载 ASR 模型。

### POST /inference/transcribe/models/cleanup

ASR 驻留清理。

### 当前用户声纹注册

用户第一次启用语音输入时，music 后端先调用：

```text
POST /asr/speaker/register/
```

请求使用 `multipart/form-data`：

| 参数 | 必填 | 说明 |
|------|------|------|
| `audio_file` | 是 | 当前用户的干净单人语音，建议 5～10 秒 |
| `speaker_id` | 是 | music 后端认证后的用户 ID |
| `name` | 是 | 展示名称 |

同一个 `speaker_id` 再次注册会更新原声纹。注销使用 `POST /asr/speaker/unregister/`，字段为 `speaker_id`；查询使用 `GET /asr/speaker/list/`。实时和单文件 ASR 必须传入同一个 `speaker_id`。

服务端默认相似度阈值为 `SPEAKER_SIMILARITY_THRESHOLD=0.75`，最短验证语音为 `SPEAKER_MIN_AUDIO_MS=1000`。阈值应使用实际设备录音做误接收/误拒绝测试后再调整。

### WebSocket /ws/asr/final（普通实时识别）

推荐给 music 后端、语音对话、LLM 语音输入使用。它不返回实时中间字幕，而是：

```text
PCM -> FSMN VAD 断句 -> final ASR -> 返回最终文本
```

连接地址：

```text
ws://host:40302/ws/asr/final
```

连接成功后，服务端会立即返回：

```json
{
  "type": "connection",
  "status": "connected",
  "message": "VAD final STT 已就绪",
  "protocol": "vad-final-v1",
  "speaker_gate": "disabled",
  "audio_format": {
    "sample_rate": 16000,
    "channels": 1,
    "sample_format": "s16le"
  }
}
```

音频输入要求与 `/ws/asr/transcribe` 相同，必须是 `16kHz / mono / signed int16 / little-endian` 裸 PCM 二进制帧。

调用流程：

```text
1. 建立 WebSocket
2. 发送 `start`，可选携带 VAD 断句参数
3. 持续发送 PCM int16 二进制帧
4. 持续接收 audio_state 和 voice_activity
5. VAD 判断一句结束后接收 result 和 commit_hint
6. 结束时发送 {"command":"stop"}
7. 接收 final_text
```

启动参数：

```json
{
  "command": "start",
  "vad": {
    "chunk_ms": 200,
    "end_silence_ms": 1200,
    "speech_noise_threshold": 0.6,
    "min_speech_duration_ms": 250,
    "preroll_ms": 1200
  }
}
```

也可以只传最小字段：

```json
{
  "command": "start",
  "end_silence_ms": 1200
}
```

未传时使用默认值：`chunk_ms=200`、`end_silence_ms=1800`、`speech_noise_threshold=0.6`、`min_speech_duration_ms=250`、`preroll_ms=1200`。

音频状态事件：

```json
{
  "type": "audio_state",
  "input_level": 0.42,
  "noise_level": 0.08,
  "clipping": false
}
```

人声活动事件：

```json
{
  "type": "voice_activity",
  "is_speech": true,
  "silence_ms": 0,
  "speech_ms": 1200
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
  "segment_index": 1,
  "source": "silence-end",
  "duration": 2.4,
  "speaker_id": null,
  "speaker_name": null,
  "speaker_similarity": null,
  "speaker_verified": false
}
```

提交建议响应：

```json
{
  "type": "commit_hint",
  "reason": "silence",
  "should_commit": true,
  "final_text": "最终识别文本，带标点。",
  "vad": {
    "end_silence_ms": 1200,
    "actual_silence_ms": 1200
  }
}
```

`commit_hint` 只表示语音服务建议提交，最终是否发送聊天消息仍由 MonCore/前端决定。

该入口不启用声纹门禁，兼容只需要持续转录的现有客户端。需要“只识别当前注册用户”时必须改用 `/ws/asr/final/voiceprint`。

### WebSocket /ws/asr/final/voiceprint（声纹实时识别）

请求音频、VAD 参数和事件结构与 `/ws/asr/final` 相同，但连接响应为 `protocol=vad-final-speaker-gate-v1`、`speaker_gate=required`。客户端持续发送 PCM；服务端在每个完整 VAD 语音段结束后先做当前个人声纹 1:1 验证，通过后才调用 ASR 并返回 `speaker_verified=true` 的 `result`。

启动命令仍为 `{"command":"start"}`。个人部署下服务端固定绑定 `PERSONAL_SPEAKER_ID`，忽略客户端伪造的其他身份。未注册、不匹配、音频过短或声纹服务异常时不会调用 ASR，也不会返回识别文本，而是返回 `warning`、`speaker_gate` 和 `should_commit=false` 的 `commit_hint`。

`reason` 可选：

| reason | 含义 |
|--------|------|
| `silence` | 检测到人声结束 |
| `manual_stop` | 用户停止录音 |

警告响应：

```json
{
  "type": "warning",
  "code": "LOW_VOLUME",
  "message": "输入音量过低"
}
```

常见 `code`：

| code | 含义 |
|------|------|
| `NO_SPEECH` | 未检测到有效人声或有效文本 |
| `LOW_VOLUME` | 输入音量过低 |
| `AUDIO_FORMAT_UNSUPPORTED` | 音频格式不是 16k mono int16 PCM |
| `VOICEPRINT_REQUIRED` | 未绑定当前用户 `speaker_id` |
| `VOICEPRINT_NOT_REGISTERED` | 当前用户尚未登记声纹 |
| `VOICEPRINT_AUDIO_TOO_SHORT` | 有效语音过短，无法可靠验证 |
| `VOICEPRINT_MISMATCH` | 说话人不是当前用户，该段语音已丢弃 |
| `VOICEPRINT_ERROR` | 声纹服务异常，按拒绝处理 |

停止响应：

```json
{
  "type": "status",
  "message": "录音结束",
  "final_text": "完整最终文本，带标点。"
}
```

### WebSocket /ws/asr/transcribe

旧的流式入口。严格声纹门禁启用后，为避免在验证前泄露文本，该接口不再返回实时中间字幕，只在完整 VAD 段通过声纹验证后返回 final。新对接的普通转录使用 `/ws/asr/final`，声纹转录使用 `/ws/asr/final/voiceprint`。

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
2. 发送 {"command":"start","speaker_id":"music-user-123"}
3. 持续发送 PCM int16 二进制帧
4. VAD 断句并通过声纹验证后接收 final
5. 结束时发送 {"command":"stop"}
6. 接收 final_text
```

连接成功响应：

```json
{
  "type": "connection",
  "status": "connected",
  "message": "声纹门禁 ASR 已就绪",
  "protocol": "speaker-gated-final-v1",
  "speaker_gate": "required",
  "interim_enabled": false
}
```

声纹拒绝响应（不包含识别文本）：

```json
{
  "type": "speaker_gate",
  "accepted": false,
  "code": "VOICEPRINT_MISMATCH",
  "speaker_id": "music-user-123",
  "speaker_similarity": 0.41
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
  "speaker_id": "music-user-123",
  "speaker_name": "当前用户",
  "speaker_similarity": 0.91,
  "speaker_verified": true
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
| WebSocket 握手返回 `403 Forbidden`，HTTP GET 同路径返回 `404` | 后端是否已部署包含 WebSocket 路由的版本；PM2 是否跑的是 `Code/FastApi/Main/run_gateway.py start --host 0.0.0.0 --port 40302 --no-reload`；前置代理是否转发 `Upgrade` |
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
  "training_workflow": null,
  "next_action": "可以开始训练模型"
}
```

当 `start_training=true` 时，接口只负责完成预处理并把训练工作流加入后台队列，不会等待全部 epoch 完成。响应中的 `training_workflow` 是可直接轮询的工作流快照：

```json
{
  "workflow_id": "training_workflow_0123456789ab",
  "status": "queued",
  "order": ["sovits", "gpt"],
  "current_target": null,
  "targets": [
    {"target": "sovits", "status": "pending", "job_id": null, "error": null},
    {"target": "gpt", "status": "pending", "job_id": null, "error": null}
  ],
  "error": null
}
```

保存 `workflow_id`，再通过下面的状态接口轮询。前一个训练目标只有在状态为 `completed` 后，后一个目标才会启动；失败或停止都会中断后续训练。

### POST /workflow/training/full

预处理 + 训练引导工作流。在 `/workflow/complete` 的基础上，支持直接上传音频文件。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_files` | file[] | 否 | - | 直接上传多个音频文件 |

其他参数与 `/workflow/complete` 相同，`start_training` 固定为 `true`。

### GET /workflow/training/status/{workflow_id}

查询后台顺序训练工作流状态。

**响应示例：**

```json
{
  "workflow_id": "training_workflow_0123456789ab",
  "project_name": "my_project",
  "project_root": "/output/my_project",
  "version": "v2Pro",
  "order": ["sovits", "gpt"],
  "status": "running",
  "current_target": "sovits",
  "targets": [
    {
      "target": "sovits",
      "job_id": "sovits_20260805_123456",
      "launch": {"success": true, "status": "running"},
      "status": "running",
      "details": null,
      "error": null
    },
    {
      "target": "gpt",
      "job_id": null,
      "launch": null,
      "status": "pending",
      "details": null,
      "error": null
    }
  ],
  "error": null
}
```

工作流状态值：`queued` / `running` / `completed` / `failed` / `stopped`。目标状态还可能是 `pending` 或 `starting`。子进程异常退出时，目标的 `error` 和工作流的 `error` 会包含日志末尾的实际错误。

### POST /workflow/training/stop/{workflow_id}

停止排队中或运行中的完整训练工作流。正在运行的 GPT/SoVITS 子进程会被终止，后续目标不会启动。接口返回停止后的完整工作流状态；对已经结束的工作流重复调用是幂等的。

注意：

- 完整工作流通过全局锁串行执行，同一时间只运行一个完整训练工作流。
- 手动调用 `/training/gpt/start` 或 `/training/sovits/start` 不受该工作流锁约束。
- 工作流状态目前保存在进程内存中；后端重启后，历史 `workflow_id` 无法继续查询。

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
