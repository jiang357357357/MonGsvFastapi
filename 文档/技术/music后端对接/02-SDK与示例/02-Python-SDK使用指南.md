# Python SDK 使用指南

> 核对日期：2026-10-24。历史 SDK 位于 `Code/FastApi/Api/`，其模型和部分请求编码尚未跟上当前网关。
> 新对接的训练与合成请优先使用下文 `requests` / `websockets` 示例，字段以 [API 手册](../01-接口协议/01-API完整手册.md) 为准。

## SDK 当前兼容边界

- SDK 仍保留固定训练 Batch 和旧保存间隔，不能据此判断服务端默认值。工作台默认值从 `/training/workbench/defaults` 获取。
- SDK 的无文件 POST 默认发送 JSON，当前训练、模型加载和多数底层接口要求表单；旧封装可能返回 422，不能直接当作已适配当前网关的客户端。
- SDK 推理封装尚未转发 `seed/sample_steps/cfg_rate/inference_mode` 等完整参数；Base64 参考音频字段也不是当前统一网关的公开入参。
- SDK 尚未封装训练工作台。本文保留的数据准备等旧 SDK 示例用于说明既有结构，未经本次调用验收；需要这些功能时按 API 手册直接发送表单。

## 安装到你的项目

SDK 无需额外安装，将项目根目录加入 `sys.path` 即可使用。

```python
import sys
sys.path.append("/path/to/MonGsvFastapi")
```

或者将 `Code/FastApi/Api/` 目录拷贝到你的项目中独立使用。

## 初始化

### 同步客户端

```python
from Code.FastApi.Api import SyncGPTSoVITSClient, get_request_builder, get_default_config
from Code.FastApi.Api import AudioUtils

# 配置
config = get_default_config()
config.set("base_url", "http://192.168.1.100:40302")  # 后端服务地址

builder = get_request_builder(config)
client = SyncGPTSoVITSClient(base_url="http://192.168.1.100:40302")
```

### 异步客户端

```python
from Code.FastApi.Api import GPTSoVITSClient

# 方式一：async with 上下文
async with GPTSoVITSClient(base_url="http://192.168.1.100:40302") as client:
    result = await client.health_check()

# 方式二：手动管理生命周期
client = GPTSoVITSClient(base_url="http://192.168.1.100:40302")
try:
    result = await client.health_check()
finally:
    await client.close()
```

## TTS 语音合成

### 推荐流程：按角色 + 情感合成

业务系统推荐调用 `POST /api/synthesis/role-emotion`。这种方式不需要调用方关心 `gpt_model_path`、`sov_model_path`、`ref_audio_path`、`prompt_text` 等底层字段。

```python
import base64
import requests

base_url = "http://192.168.1.100:40302"

payload = {
    "world_id": 1,
    "version": "v2Pro",
    "role_id": 1,
    "emotion": "温柔",
    "text": "博士，今天也辛苦了。",
    "text_language": "zh",
    "speed": 1.0,
    "how_to_cut": "按标点符号切",
    "return_base64": True,
}

response = requests.post(f"{base_url}/api/synthesis/role-emotion", json=payload)
response.raise_for_status()
data = response.json()

if data.get("success"):
    with open("output.wav", "wb") as f:
        f.write(base64.b64decode(data["audio_data"]))
else:
    raise RuntimeError(data.get("message") or "合成失败")
```

后端会自动完成：

1. 根据 `role_id` 查角色。
2. 根据 `emotion` 查情感配置。
3. 使用角色的 `gpt_model_path` / `sov_model_path` 自动加载模型。
4. 使用情感的 `music_url` / `text` / `text_language` 作为参考音频和参考文本。
5. 调用底层推理并返回音频。

### 高级流程：表单加载模型与自定义参考音频

模型路径和 `ref_audio_path` 指服务端文件；客户端本地参考文件请通过 `files={"ref_audio": ...}` 上传。

```python
import base64
import requests

base_url = "http://localhost:40302"
response = requests.post(
    f"{base_url}/inference/models/load",
    data={"gpt_path": "/models/voice.ckpt", "sovits_path": "/models/voice.pth"},
    timeout=600,
)
response.raise_for_status()
loaded = response.json()
if not loaded.get("success"):
    raise RuntimeError(loaded.get("message") or "模型加载失败")

with open("ref.wav", "rb") as reference:
    response = requests.post(
        f"{base_url}/inference/tts",
        data={
            "text": "你好，欢迎使用语音合成系统。",
            "text_language": "zh",
            "prompt_text": "参考音频中的准确文本。",
            "prompt_language": "zh",
            "seed": 2027,
            "top_k": 15,
            "top_p": 1.0,
            "temperature": 1.0,
            "pause_second": 0.3,
            "inference_mode": "normal",
            "return_base64": "true",
        },
        files={"ref_audio": ("ref.wav", reference, "audio/wav")},
        timeout=600,
    )
response.raise_for_status()
result = response.json()
if not result.get("success"):
    raise RuntimeError(result.get("message") or "合成失败")
with open("output.wav", "wb") as output:
    output.write(base64.b64decode(result["audio_data"]))
```

未传 `sample_steps/cfg_rate` 时按模型取默认：V3=32 步，V4=8 步，V5dev=32 步/CFG 1.30，V5turbo=4 步/CFG 0。可选步数为 4、8、16、32，CFG 范围 0–2。`seed=-1` 表示随机，固定种子范围为 0–4294967295。

HTTP 保留合法的 `top_p=0` 和 `temperature=0`；`pause_second` 范围为 0.1–0.5 秒。`if_freeze` 当前没有冻结效果。`normal` 关闭 CUDA Graph/FlashAttention，`accelerated` 同时尝试两个开关。当前网关输出 WAV，不接受官方 `media_type` 或 Base64 参考音频字段。

### TTS WebSocket：按模型返回 Token 块或完整片段

`ready.stream_mode` 在 V1/V2/Pro 系列为 `tokens`，V3/V4/V5 为 `segments`。后者要等本段生成后才返回，V5 输出 48 kHz。当前尚未接入官方最新 `gpt_streaming`。

WS 不转发 `seed`，`top_p=0` 和 `temperature=0` 会被替换成 1；固定种子或零值采样请用 HTTP。WS 推理固定关闭两个加速开关。取消只停止会话输出，后台计算可能继续；客户端应清空播放缓冲。

在 SDK 增加正式封装前，可以直接使用 `websockets`。`role_id` 和 `emotion` 应先通过资源接口动态获取：

```python
import asyncio
import json
import wave

import websockets


async def stream_tts():
    pcm = bytearray()
    sample_rate = None

    async with websockets.connect("ws://localhost:40302/ws/tts/stream") as ws:
        await ws.send(json.dumps({
            "type": "start",
            "request_id": "music-tts-001",
            "role_id": 427041150,  # 示例快照；实际调用前查询 /api/role/list/
            "emotion": "淡然",
            "text_language": "zh",
            "how_to_cut": "按标点符号切",
            "top_k": 15,
            "top_p": 1.0,
            "temperature": 1.0,
            "pause_second": 0.3,
        }, ensure_ascii=False))

        # start 阶段可能先收到 status，等待 ready 后再发送文本。
        while True:
            event = json.loads(await ws.recv())
            if event.get("type") == "ready":
                break
            if event.get("type") == "error":
                raise RuntimeError(event.get("message"))

        await ws.send(json.dumps({
            "type": "text",
            "request_id": "music-tts-001",
            "text": "老师，今天需要处理的工作已经整理完毕。请您按顺序确认。",
        }, ensure_ascii=False))
        await ws.send(json.dumps({
            "type": "finish",
            "request_id": "music-tts-001",
        }))

        while True:
            message = await ws.recv()
            if isinstance(message, bytes):
                pcm.extend(message)
                continue

            event = json.loads(message)
            if event.get("type") == "audio_start":
                sample_rate = int(event["sample_rate"])
            elif event.get("type") == "error":
                raise RuntimeError(event.get("message"))
            elif event.get("type") == "end":
                break

    if not sample_rate:
        raise RuntimeError("服务端没有返回音频")

    with wave.open("stream_output.wav", "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


asyncio.run(stream_tts())
```

示例为了便于验证而在结束后写 WAV。实时播放时，应在收到每个二进制 PCM 块后立即放入播放队列，不要等待 `end`。

## 模型管理

```python
# 查看当前模型信息
info = client.get_model_info()
print(info)

# 卸载模型（释放显存）
client.unload_models()

# 清理驻留缓存
client.cleanup_resident_models(force=True)
```

## 数据准备

### 音频切分

```python
request = builder.audio_slice_request(
    input_path="/audio/long_audio.wav",   # 输入音频文件或目录
    output_dir="/output/sliced",          # 输出目录
    threshold=-34.0,                      # 切分阈值
    min_length=4000                       # 最小切片长度(ms)
)
response = client.audio_slice(request)
print(f"切分完成，输出 {len(response.output_files)} 个文件")
```

### ASR 语音识别

```python
request = builder.asr_request(
    input_path="/audio/sliced",           # 音频目录
    output_file="/output/asr/result.list", # 输出位置提示，真实路径读取 response.output_file
    language="zh"
)
response = client.asr_recognize(request)
print(f"识别结果文件：{response.output_file}")
```

统一网关的训练/数据准备 ASR 根据 `language` 自动选引擎：`zh`、`yue` 使用 FunASR，英语、日语、韩语等使用 Faster-Whisper。SDK 请求模型中虽然保留 `model_type` 等字段，但 `/data-prep/asr/recognize` 当前不会据此覆盖语言分流。传入的 `output_file` 只提供输出目录提示，实际生成文件名以响应字段为准。

## 数据集格式化

```python
# 文本特征提取
request = builder.text_processing_request(
    list_file="/output/asr/result.list",
    output_dir="/output/dataset",
    language="zh"
)
response = client.text_processing(request)

# 音频特征提取
request = builder.audio_features_request(
    list_file="/output/asr/result.list",
    output_dir="/output/dataset",
    version="v2Pro"
)
response = client.audio_features(request)

# 语义编码
request = builder.semantic_encoding_request(
    list_file="/output/asr/result.list",
    output_dir="/output/dataset",
    version="v2Pro"
)
response = client.semantic_encoding(request)
```

## 训练

推荐直接对接工作台。下例使用已有角色和服务端原始音频目录；首次创建角色可改为 `role_mode="new"`。上传模式把本地文件作为重复的 `audio_files` multipart 字段发送，文件句柄需保持到请求结束。

```python
import json
import time
import requests

base_url = "http://localhost:40302"
session = requests.Session()
# 如果服务启用了 HTTP 认证：
# session.headers["Authorization"] = "Bearer your-api-key"

response = session.get(f"{base_url}/training/workbench/defaults", timeout=30)
response.raise_for_status()
print(response.json()["versions"]["v5turbo"])

options = {
    "world_name": "DemoWorld",
    "project_name": "DemoVoice",
    "version": "v5turbo",
    "role_mode": "existing",
    "training_mode": "fresh",
    "preprocessing_mode": "full",
    "input_audio_dir": "/data/audio/raw",
    "language": "zh",
    "gpu_numbers": "0",
    "train_gpt": True,
    "train_sovits": True,
}
# files 中的空文件名用于将 options 编码为 multipart 文本字段。
response = session.post(
    f"{base_url}/training/workbench/start",
    files={"options": (None, json.dumps(options, ensure_ascii=False))},
    timeout=120,
)
response.raise_for_status()
workflow_id = response.json()["training_workflow"]["workflow_id"]

while True:
    response = session.get(
        f"{base_url}/training/workbench/runs/{workflow_id}", timeout=60
    )
    response.raise_for_status()
    record = response.json()
    print(record["status"], record.get("current_target"))
    if record["status"] in {"completed", "failed", "stopped", "interrupted"}:
        break
    time.sleep(5)
```

记录跨重启保留，未结束任务会标为 `interrupted`。续训前查询 `/training/workbench/workspaces`，设置 `training_mode="resume"` 与返回的 `resume_workspace`；总轮数是累计目标，必须超过已完成轮数。

GPT 默认 15 轮；普通 SoVITS 默认 8 轮，V3/V4/V5 默认 2 轮。Batch、精度按硬件选择；GPT/SoVITS 学习率分别为 0.01/0.0001。默认只在各阶段最后一轮保存权重与恢复 checkpoint，中途停止可能没有新增可恢复进度。

停止、日志和试听：

```python
response = session.get(
    f"{base_url}/training/workbench/runs/{workflow_id}/logs",
    params={"target": "sovits"},
    timeout=30,
)
response.raise_for_status()
print(response.json()["text"])

# 需要停止仍在运行的任务时：
# session.post(f"{base_url}/training/workbench/runs/{workflow_id}/stop", timeout=60)
# 完成后可 POST 同一 /runs/{workflow_id}/preview，
# JSON 为 {"text": "试听文本", "emotion": "现有情感名", "seed": 2027}。
```

单项 `/training/gpt/start` 与 `/training/sovits/start` 仅接收基础表单字段，不接收 SDK 全部训练配置；高级字段请用工作台。V1 文本特征版本传递仍有已知限制，详见 [训练与模型](../04-训练与模型/README.md)。

## 工作流

下节为旧工作流封装，预处理在 HTTP 请求内执行。新训练优先使用上文工作台；两组 `workflow_id` 的查询路径和持久化行为不同。

### 一键预处理工作流

```python
from Code.FastApi.Api import WorkflowConfig, WorkflowRequest

request = builder.workflow_request(
    project_name="my_project",
    input_audio_dir="/audio/raw/",
    output_dir="/output/",
    language="zh",
    version="v2Pro",
    skip_existing=True,
    parallel_processing=True
)
response = client.complete_workflow(request)
for step in response.steps:
    print(f"{step['step']}: {'成功' if step['result'].get('success') else '失败'}")
```

如果工作流启用了训练，HTTP 请求会在训练排队后返回，不会等待全部 epoch 完成。当前 SDK 尚未封装顺序训练工作流状态方法，可以直接请求网关：

```python
import time
import requests

# 从启动完整训练接口返回的原始 JSON 中取得
workflow_result = requests.post(
    "http://localhost:40302/workflow/complete",
    data={
        "project_name": "my_project",
        "input_audio_dir": "/data/audio/raw",
        "output_dir": "/data/output",
        "start_training": True,
    },
    timeout=3600,
).json()
workflow_id = workflow_result["training_workflow"]["workflow_id"]

while True:
    result = requests.get(
        f"http://localhost:40302/workflow/training/status/{workflow_id}",
        timeout=30,
    ).json()
    print(result["status"], result.get("current_target"))
    if result["status"] in {"completed", "failed", "stopped"}:
        break
    time.sleep(30)
```

该状态保存在网关进程内存中；后端重启后不能继续查询旧 `workflow_id`。

停止整个工作流时请求 `POST /workflow/training/stop/{workflow_id}`；它会同时终止当前训练子进程并阻止后续目标启动。

## 批量处理

```python
from Code.FastApi.Api.models import BatchProject

project_a = BatchProject(
    name="project_a",
    input_dir="/audio/project_a",
    output_dir="/output/project_a",
    language="zh",
    version="v2Pro"
)
project_b = BatchProject(
    name="project_b",
    input_dir="/audio/project_b",
    output_dir="/output/project_b",
    language="en",
    version="v2Pro"
)

request = builder.batch_request(
    batch_name="test_batch",
    projects=[project_a, project_b],
    max_concurrent=2
)
response = client.batch_process(request)
```

## 错误处理

```python
from Code.FastApi.Api import (
    GPTSoVITSAPIError,
    ServiceUnavailableError,
    ValidationError,
    AuthenticationError,
    TimeoutError,
    RateLimitError
)

try:
    response = client.inference(request)
except ServiceUnavailableError as e:
    print(f"服务不可用：{e}")
except ValidationError as e:
    print(f"参数错误：{e}")
except AuthenticationError as e:
    print(f"认证失败，请检查 API Key")
except TimeoutError as e:
    print(f"请求超时")
except RateLimitError as e:
    print(f"请求频率过高")
except GPTSoVITSAPIError as e:
    print(f"API 错误：{e} (HTTP {e.status_code})")
```

## 配置管理

```python
from Code.FastApi.Api import APIConfig

# 自定义配置文件
config = APIConfig(config_file="/path/to/my_config.json")

# 或修改默认配置
config = get_default_config()
config.set("base_url", "http://192.168.1.100:40302")
config.set("default_language", "zh")
config.set("default_version", "v2Pro")
config.set("timeout", 600)
config.set("max_retries", 5)

# 批量更新
config.update({
    "base_url": "http://192.168.1.100:40302",
    "timeout": 1200
})

# 重置为默认
config.reset_to_default()
```

## 工具方法

```python
from Code.FastApi.Api import AudioUtils, create_temp_audio_file

# 获取音频文件信息
info = AudioUtils.get_audio_info("audio.wav")
# => { duration, sample_rate, channels, frames, format, file_size }

# 验证音频文件
AudioUtils.validate_audio_file("audio.wav", min_duration=1.0, max_duration=30.0)

# 采样率转换
AudioUtils.convert_sample_rate("input.wav", "output.wav", target_rate=32000)

# 音量标准化
AudioUtils.normalize_audio("input.wav", "output.wav", target_db=-20.0)

# 创建临时测试音频
temp_file = create_temp_audio_file(duration=5.0, sample_rate=22050)

# Base64 编解码
base64_data = AudioUtils.encode_audio_file("audio.wav")
AudioUtils.decode_audio_base64(base64_data, "decoded.wav")
```

## 运行官方演示脚本

项目自带完整演示脚本 `Code/FastApi/Api/demo.py`，覆盖所有功能：

```bash
# 运行全部演示
python Code/FastApi/Api/demo.py --url http://localhost:40302

# 运行指定演示
python Code/FastApi/Api/demo.py --url http://localhost:40302 --demo health
python Code/FastApi/Api/demo.py --url http://localhost:40302 --demo inference
python Code/FastApi/Api/demo.py --url http://localhost:40302 --demo training

# 演示类型列表
python Code/FastApi/Api/demo.py --help
```

## 完整类型参考

SDK 中所有 Pydantic 模型定义一览：

### 请求模型

| 类名 | 用途 |
|------|------|
| `AudioSliceRequest` | 音频切分请求 |
| `ASRRequest` | ASR 识别请求 |
| `VoiceSeparationRequest` | 人声分离请求 |
| `TextProcessingRequest` | 文本特征提取请求 |
| `AudioFeaturesRequest` | 音频特征提取请求 |
| `SemanticEncodingRequest` | 语义编码请求 |
| `DatasetValidationRequest` | 数据集验证请求 |
| `GPTTrainingRequest` | GPT 训练请求 |
| `SoVITSTrainingRequest` | SoVITS 训练请求 |
| `InferenceRequest` | TTS 推理请求 |
| `BatchInferenceRequest` | 批量 TTS 请求 |
| `ModelLoadRequest` | 模型加载请求 |
| `WorkflowRequest` | 工作流请求 |
| `BatchRequest` | 批量处理请求 |

### 响应模型

| 类名 | 用途 |
|------|------|
| `AudioSliceResponse` | 音频切分结果 |
| `ASRResponse` | ASR 识别结果 |
| `TextProcessingResponse` | 文本特征结果 |
| `AudioFeaturesResponse` | 音频特征结果 |
| `SemanticEncodingResponse` | 语义编码结果 |
| `DatasetValidationResponse` | 数据集验证结果 |
| `GPTTrainingResponse` | GPT 训练结果（含 job_id） |
| `SoVITSTrainingResponse` | SoVITS 训练结果 |
| `TrainingStatus` | 训练状态 |
| `InferenceResponse` | TTS 推理结果 |
| `InferenceResult` | 单条推理结果 |
| `BatchInferenceResponse` | 批量推理结果 |
| `ModelListResponse` | 模型列表 |
| `ModelLoadResponse` | 模型加载结果 |
| `WorkflowResponse` | 工作流结果 |
| `BatchResponse` | 批量处理结果 |

### 配置模型

| 类名 | 用途 |
|------|------|
| `AudioSliceConfig` | 音频切分配置 |
| `ASRConfig` | ASR 配置 |
| `TextProcessingConfig` | 文本处理配置 |
| `AudioFeaturesConfig` | 音频特征配置 |
| `SemanticEncodingConfig` | 语义编码配置 |
| `GPTTrainingConfig` | GPT 训练配置 |
| `SoVITSTrainingConfig` | SoVITS 训练配置 |
| `InferenceConfig` | 推理配置 |
| `WorkflowConfig` | 工作流配置 |

### 异常类

| 类名 | HTTP 状态码 | 说明 |
|------|-------------|------|
| `GPTSoVITSAPIError` | 任意 | 基础异常 |
| `ServiceUnavailableError` | 503 | 服务不可用 |
| `ValidationError` | 400 | 参数校验失败 |
| `ProcessingError` | 500 | 处理过程异常 |
| `AuthenticationError` | 401 | 认证失败 |
| `RateLimitError` | 429 | 频率限制 |
| `TimeoutError` | 408 | 请求超时 |
