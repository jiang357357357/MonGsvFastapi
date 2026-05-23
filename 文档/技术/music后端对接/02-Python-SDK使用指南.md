# Python SDK 使用指南

> 项目内置了一套完整的 Python 客户端 SDK，位于 `Code/FastApi/Api/`。
> 支持同步/异步两种模式，类型完备（Pydantic），自带请求构建器和异常体系。

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

### 基本流程：加载模型 -> 推理

```python
# 1. 加载模型
client.load_models(
    gpt_path="GPT_weights_v2Pro/my_role.ckpt",       # GPT 权重路径
    sovits_path="SoVITS_weights_v2Pro/my_role.pth"    # SoVITS 权重路径
)

# 2. 构建推理请求
request = builder.inference_request(
    text="你好，欢迎使用语音合成系统。",
    ref_audio_path="/path/to/reference_audio.wav",
    prompt_text="这是一段参考音频的文本内容。",
    text_language="zh",
    prompt_language="zh",
    top_k=20,
    top_p=0.6,
    temperature=0.6,
    speed=1.0,
    how_to_cut="凑四句一切",
    return_base64=True  # 返回 base64 编码的音频
)

# 3. 执行推理
response = client.inference(request)

if response.success:
    # 保存音频文件
    AudioUtils.decode_audio_base64(response.audio_data, "output.wav")
    print(f"音频已保存，时长：{response.duration:.2f}秒")
    print(f"处理耗时：{response.processing_time:.2f}秒")
else:
    print(f"推理失败：{response.message}")
```

### 方式二：Base64 音频作为参考

无需文件路径，直接传入 base64 编码的音频数据：

```python
import base64

with open("ref.wav", "rb") as f:
    ref_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

request = builder.inference_request(
    text="这是使用 Base64 参考音频的测试。",
    ref_audio_base64=ref_audio_b64,
    prompt_text="参考音频的文字。",
    return_base64=True
)

response = client.inference(request)
```

或者使用内置工具：

```python
ref_audio_b64 = AudioUtils.encode_audio_file("ref.wav")
```

### 方式三：直接传参（不经过 Builder）

```python
from Code.FastApi.Api import InferenceRequest, InferenceConfig

request = InferenceRequest(
    text="直接传参的测试。",
    text_language="zh",
    ref_audio_path="/path/to/ref.wav",
    prompt_text="参考文本",
    prompt_language="zh",
    config=InferenceConfig(
        top_k=20,
        top_p=0.6,
        temperature=0.6,
        speed=1.0,
        how_to_cut="不切"
    ),
    return_base64=True
)
response = client.inference(request)
```

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
    output_file="/output/asr/result.list", # 输出标注文件
    model_type="funasr",
    language="zh"
)
response = client.asr_recognize(request)
print(f"识别结果文件：{response.output_file}")
```

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

### GPT 训练

```python
request = builder.gpt_training_request(
    exp_name="my_project",
    exp_root="/output/my_project",
    batch_size=8,
    total_epoch=15,
    learning_rate=0.0001
)
response = client.start_gpt_training(request)
job_id = response.job_id
print(f"GPT 训练已启动，任务 ID：{job_id}")

# 轮询训练状态
import time
while True:
    status = client.get_training_status(job_id)
    print(f"进度：{status.progress}% / 状态：{status.status}")
    if status.status in ("completed", "failed", "stopped"):
        break
    time.sleep(30)
```

### SoVITS 训练

```python
request = builder.sovits_training_request(
    exp_name="my_project",
    exp_root="/output/my_project",
    version="v2Pro",
    batch_size=32,
    total_epoch=8
)
response = client.start_sovits_training(request)
```

### 异步等待训练完成

```python
# 阻塞等待，超时 1 小时，每 30 秒检查一次
status = client.wait_for_training_completion(job_id, check_interval=30, max_wait_time=3600)
print(f"训练完成，最终状态：{status.status}")
```

## 工作流

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
