# curl 与 HTTP 调用示例

> 所有示例基于 `http://localhost:40302`，替换为你的实际服务地址即可。
> 适用于 Java、Go、Node.js 等非 Python 项目对接参考。

---

## 目录

1. [基础验证](#1-基础验证)
2. [TTS 推理完整流程](#2-tts-推理完整流程)
3. [ASR 语音识别](#3-asr-语音识别)
4. [数据预处理](#4-数据预处理)
5. [数据集格式化](#5-数据集格式化)
6. [模型训练](#6-模型训练)
7. [工作流（一键式）](#7-工作流一键式)
8. [资源管理 CRUD](#8-资源管理-crud)
9. [JavaScript fetch 示例](#9-javascript-fetch-示例)

---

## 1. 基础验证

### 服务信息

```bash
curl -s "http://localhost:40302/" | python -m json.tool
```

```json
{
  "service": "GPT-SoVITS 统一网关",
  "version": "2.1.0",
  "status": "running",
  "available_services": ["audio_slice", "asr_recognition", "text_processing", "audio_features", "semantic_encoding", "gpt_training", "sovits_training", "inference"],
  "documentation": "/docs"
}
```

### 健康检查

```bash
curl -s "http://localhost:40302/health" | python -m json.tool
```

```json
{
  "gateway_status": "healthy",
  "services": {
    "audio_slice": { "status": "available" },
    "asr_recognition": { "status": "available" },
    "inference": { "status": "available" }
  },
  "total_services": 8,
  "healthy_services": 8
}
```

### 服务状态

```bash
curl -s "http://localhost:40302/services/status" | python -m json.tool
```

---

## 2. TTS 推理完整流程

### 推荐流程：按角色 + 情感合成

这是前端和 music 后端推荐使用的接口。调用方只需要传业务字段，后端会自动加载角色模型，并从情感配置中取参考音频和参考文本。

```bash
curl -X POST "http://localhost:40302/api/synthesis/role-emotion" \
  -H "Content-Type: application/json" \
  -d '{
    "world_id": 1,
    "version": "v2Pro",
    "role_id": 1,
    "emotion": "温柔",
    "text": "博士，今天也辛苦了。",
    "text_language": "zh",
    "speed": 1.0,
    "how_to_cut": "凑四句一切",
    "use_cuda_graph": false,
    "return_base64": true
  }' \
  -o tts_response.json
```

解析结果保存音频：

```bash
cat tts_response.json | jq -r '.audio_data' | base64 -d > output.wav
```

完整业务链路：

```bash
# 1. 查世界
curl -s "http://localhost:40302/api/world/list/" | python -m json.tool

# 2. 查版本
curl -s "http://localhost:40302/api/models/versions/from-enum/" | python -m json.tool

# 3. 查角色，记录 role.id
curl -s "http://localhost:40302/api/role/list/?world_id=1&version=v2Pro" | python -m json.tool

# 4. 查情感，记录 emotions[].name
curl -s "http://localhost:40302/api/role/emotions/?role_id=1" | python -m json.tool

# 5. 用 role_id + emotion 合成
curl -X POST "http://localhost:40302/api/synthesis/role-emotion" \
  -H "Content-Type: application/json" \
  -d '{"role_id":1,"emotion":"温柔","text":"你好。","text_language":"zh"}'
```

### 高级流程：直接调用底层推理接口

底层 `/inference/tts` 不会自动解析角色或情感。调用方必须先加载模型，并显式传 `ref_audio` 或 `ref_audio_path`。

### 步骤一：加载模型

```bash
curl -X POST "http://localhost:40302/inference/models/load" \
  -F "gpt_path=GPT_weights_v2Pro/my_role.ckpt" \
  -F "sovits_path=SoVITS_weights_v2Pro/my_role.pth"
```

响应：
```json
{
  "success": true,
  "message": "模型加载成功",
  "gpt_path": "GPT_weights_v2Pro/my_role.ckpt",
  "sovits_path": "SoVITS_weights_v2Pro/my_role.pth"
}
```

### 步骤二：语音合成（上传参考音频）

```bash
curl -X POST "http://localhost:40302/inference/tts" \
  -F "text=你好，欢迎使用语音合成系统。这是一段测试语音。" \
  -F "text_language=zh" \
  -F "ref_audio=@/path/to/reference.wav" \
  -F "prompt_text=参考音频的文本内容。" \
  -F "prompt_language=zh" \
  -F "how_to_cut=凑四句一切" \
  -F "top_k=20" \
  -F "top_p=0.6" \
  -F "temperature=0.6" \
  -F "speed=1.0" \
  -F "sample_steps=8" \
  -F "use_cuda_graph=false" \
  -F "return_base64=true" \
  -o tts_response.json
```

`use_cuda_graph=true` 只建议在 CUDA 服务端、普通非流式单条推理时开启。失败时后端会打印 `[cuda-graph]` 日志并自动回退普通推理。

解析结果保存音频：

```bash
# 用 jq 提取 base64 并解码
cat tts_response.json | jq -r '.audio_data' | base64 -d > output.wav

# 或者用 Python
python -c "
import json
with open('tts_response.json') as f:
    data = json.load(f)
with open('output.wav', 'wb') as f:
    f.write(__import__('base64').b64decode(data['audio_data']))
print(f'时长: {data[\"duration\"]}s, 处理耗时: {data[\"processing_time\"]}s')
"
```

### 步骤二（替代）：用服务端路径的参考音频

```bash
curl -X POST "http://localhost:40302/inference/tts" \
  -F "text=你好，欢迎使用语音合成系统。" \
  -F "text_language=zh" \
  -F "ref_audio_path=/data/resources/ref.wav" \
  -F "prompt_text=参考文本内容。" \
  -F "return_base64=true" \
  -o tts_response.json
```

### 步骤三：获取模型信息

```bash
curl -s "http://localhost:40302/inference/models/info" | python -m json.tool
```

### 步骤四：卸载模型

```bash
curl -X POST "http://localhost:40302/inference/models/unload"
```

### 获取参考音频文件

参考音频路径必须在 `Resources/Model/` 目录下才允许访问：

```bash
curl -s "http://localhost:40302/inference/ref-audio?path=Resources/Model/Standalone/小明/v2Pro/ref.wav" -o ref_audio.wav
```

---

## 3. ASR 语音识别

### 上传音频文件识别

```bash
curl -X POST "http://localhost:40302/inference/transcribe" \
  -F "audio_file=@/path/to/speech.wav" \
  -F "language=zh" \
  -F "model_type=funasr"
```

响应：
```json
{
  "success": true,
  "message": "ASR识别完成",
  "text": "今天的天气真好，适合出门散步。",
  "language": "zh",
  "segments": [
    { "text": "今天的天气真好", "start": 0.0, "end": 2.1, "language": "zh" }
  ],
  "processing_time": 1.5
}
```

### 指定音频路径识别

```bash
curl -X POST "http://localhost:40302/data-prep/asr/recognize" \
  -F "audio_dir=/data/audio/sliced" \
  -F "output_file=/data/output/asr/result.list" \
  -F "language=zh"
```

### 预加载 ASR 模型

```bash
curl -X POST "http://localhost:40302/inference/transcribe/models/load" \
  -F "model_type=funasr" \
  -F "model_size=large" \
  -F "language=zh"
```

---

## 4. 数据预处理

### 音频切分

```bash
curl -X POST "http://localhost:40302/data-prep/audio-slice/process" \
  -F "input_path=/data/audio/raw" \
  -F "output_dir=/data/audio/sliced" \
  -F "threshold=-34.0" \
  -F "min_length=4000"
```

---

## 5. 数据集格式化

### 文本特征提取

```bash
curl -X POST "http://localhost:40302/dataset/text/extract" \
  -F "list_file=/data/output/asr/result.list" \
  -F "input_wav_dir=/data/audio/sliced" \
  -F "experiment_name=my_project" \
  -F "output_dir=/data/output/dataset"
```

### 音频特征提取

```bash
curl -X POST "http://localhost:40302/dataset/audio/extract" \
  -F "list_file=/data/output/asr/result.list" \
  -F "input_wav_dir=/data/audio/sliced" \
  -F "experiment_name=my_project" \
  -F "output_dir=/data/output/dataset" \
  -F "version=v2Pro"
```

### 语义编码

```bash
curl -X POST "http://localhost:40302/dataset/semantic/encode" \
  -F "list_file=/data/output/asr/result.list" \
  -F "experiment_name=my_project" \
  -F "output_dir=/data/output/dataset" \
  -F "version=v2Pro"
```

---

## 6. 模型训练

### 启动 GPT 训练

```bash
curl -X POST "http://localhost:40302/training/gpt/start" \
  -F "exp_name=my_project" \
  -F "workspace_dir=/data/output/my_project" \
  -F "version=v2Pro" \
  -F "batch_size=8" \
  -F "total_epoch=15"
```

响应：
```json
{
  "success": true,
  "message": "GPT训练已启动",
  "job_id": "gpt_20260522_123456",
  "exp_name": "my_project",
  "status": "running",
  "config_file": "/data/output/my_project/config.yaml"
}
```

### 启动 SoVITS 训练

```bash
curl -X POST "http://localhost:40302/training/sovits/start" \
  -F "exp_name=my_project" \
  -F "workspace_dir=/data/output/my_project" \
  -F "version=v2Pro" \
  -F "batch_size=32" \
  -F "total_epoch=8"
```

### 查询训练状态

```bash
curl -s "http://localhost:40302/training/status/gpt_20260522_123456" | python -m json.tool
```

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
    "elapsed_time": 1234.5
  }
}
```

### 停止训练

```bash
curl -X POST "http://localhost:40302/training/stop/gpt_20260522_123456"
```

---

## 7. 工作流（一键式）

### 完整预处理工作流（不含训练）

```bash
curl -X POST "http://localhost:40302/workflow/complete" \
  -F "project_name=my_project" \
  -F "input_audio_dir=/data/audio/raw" \
  -F "output_dir=/data/output" \
  -F "language=zh" \
  -F "version=v2Pro" \
  -F "world_name=Standalone" \
  -F "start_training=false"
```

### 完整预处理 + 训练

```bash
curl -X POST "http://localhost:40302/workflow/complete" \
  -F "project_name=my_project" \
  -F "input_audio_dir=/data/audio/raw" \
  -F "output_dir=/data/output" \
  -F "language=zh" \
  -F "version=v2Pro" \
  -F "start_training=true" \
  -F "train_gpt=true" \
  -F "train_sovits=true" \
  -F "gpt_batch_size=8" \
  -F "gpt_total_epoch=15" \
  -F "sovits_batch_size=32" \
  -F "sovits_total_epoch=8" \
  -F "training_order=sovits_first"
```

### 训练引导工作流（带上传音频）

```bash
curl -X POST "http://localhost:40302/workflow/training/full" \
  -F "project_name=my_project" \
  -F "input_audio_dir=/data/audio/raw" \
  -F "output_dir=/data/output" \
  -F "language=zh" \
  -F "version=v2Pro" \
  -F "audio_files=@/path/to/audio1.wav" \
  -F "audio_files=@/path/to/audio2.wav"
```

### 批量处理

```bash
curl -X POST "http://localhost:40302/batch/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "projects": [
      {
        "name": "project_a",
        "input_dir": "/data/audio/project_a",
        "output_dir": "/data/output/project_a",
        "language": "zh",
        "version": "v2Pro"
      },
      {
        "name": "project_b",
        "input_dir": "/data/audio/project_b",
        "output_dir": "/data/output/project_b",
        "language": "en",
        "version": "v2Pro"
      }
    ]
  }'
```

---

## 8. 资源管理 CRUD

### World

```bash
# 列出世界
curl -s "http://localhost:40302/api/world/list/" | python -m json.tool

# 创建世界
curl -X POST "http://localhost:40302/api/world/create/" \
  -H "Content-Type: application/json" \
  -d '{"name": "我的世界", "description": "角色分组"}'

# 删除世界
curl -X POST "http://localhost:40302/api/world/delete/" \
  -H "Content-Type: application/json" \
  -d '{"id": 1}'
```

### Role

```bash
# 列出角色
curl -s "http://localhost:40302/api/role/list/?world_name=Standalone" | python -m json.tool

# 创建角色
curl -X POST "http://localhost:40302/api/role/create/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "小明",
    "world_id": 1,
    "version": "v2Pro",
    "description": "测试角色"
  }'

# 导入角色（上传权重文件）
curl -X POST "http://localhost:40302/api/role/import/" \
  -F "name=小明" \
  -F "world_id=1" \
  -F "version=v2Pro" \
  -F "gpt_file=@/path/to/model.ckpt" \
  -F "sov_file=@/path/to/model.pth" \
  -F "prompt_audio=@/path/to/ref.wav" \
  -F "prompt_text=参考文本"

# 更新角色
curl -X POST "http://localhost:40302/api/role/update/" \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "小明(更新)", "world_id": 1}'

# 删除角色
curl -X POST "http://localhost:40302/api/role/delete/" \
  -H "Content-Type: application/json" \
  -d '{"id": 1}'
```

### 情感配置

```bash
# 列出情感
curl -s "http://localhost:40302/api/role/emotions/?role_id=1" | python -m json.tool

# 创建/更新情感
curl -X POST "http://localhost:40302/api/role/emotions/upsert/" \
  -F "role_id=1" \
  -F "emotion_name=开心" \
  -F "emotion_text=今天真是太开心了！" \
  -F "text_language=zh" \
  -F "audio_file=@/path/to/happy.wav"

# 删除情感
curl -X POST "http://localhost:40302/api/role/emotions/delete/" \
  -F "role_id=1" \
  -F "emotion_name=开心"
```

### 角色工作区

```bash
# 创建工作区
curl -X POST "http://localhost:40302/api/role/workspace/create/" \
  -H "Content-Type: application/json" \
  -d '{"role_name": "小明"}'

# 列出工作区
curl -s "http://localhost:40302/api/role/workspace/list/" | python -m json.tool

# 上传训练音频
curl -X POST "http://localhost:40302/api/role/workspace/upload-audio/" \
  -F "role_name=小明" \
  -F "target=raw" \
  -F "create_if_missing=true" \
  -F "files=@/path/to/train1.wav" \
  -F "files=@/path/to/train2.wav"

# 初始化完整工作区
curl -X POST "http://localhost:40302/api/role/workspace/initialize/" \
  -F "role_name=小明" \
  -F "description=全新角色" \
  -F "world_name=Standalone" \
  -F "language=zh-CN" \
  -F "version=v2Pro" \
  -F "raw_files=@/path/to/audio1.wav" \
  -F "raw_files=@/path/to/audio2.wav"
```

### Model 权重列表

```bash
# GPT 权重列表
curl -s "http://localhost:40302/api/gpt/list/" | python -m json.tool

# SoVITS 权重列表
curl -s "http://localhost:40302/api/sov/list/" | python -m json.tool
```

### Version 版本列表

```bash
# 内置版本枚举
curl -s "http://localhost:40302/api/models/versions/from-enum/" | python -m json.tool

# 目录扫描版本
curl -s "http://localhost:40302/api/models/versions/from-dir/" | python -m json.tool
```

---

## 9. JavaScript fetch 示例

### TTS 推理（推荐：按角色 + 情感）

```javascript
async function synthesizeByRoleEmotion({ roleId, emotion, text, worldId, version }) {
  const res = await fetch('http://localhost:40302/api/synthesis/role-emotion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      role_id: roleId,
      world_id: worldId,
      version,
      emotion,
      text,
      text_language: 'zh',
      speed: 1.0,
      how_to_cut: '凑四句一切',
      return_base64: true,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || error.message || `HTTP ${res.status}`);
  }

  return res.json();
}

async function main() {
  const result = await synthesizeByRoleEmotion({
    worldId: 1,
    version: 'v2Pro',
    roleId: 1,
    emotion: '温柔',
    text: '博士，今天也辛苦了。',
  });

  if (result.success) {
    playBase64Audio(result.audio_data);
  }
}
```

### TTS 推理（高级：底层接口）

```javascript
// 加载模型
async function loadModels(gptPath, sovitsPath) {
  const formData = new FormData();
  formData.append('gpt_path', gptPath);
  formData.append('sovits_path', sovitsPath);

  const res = await fetch('http://localhost:40302/inference/models/load', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

// 语音合成（上传参考音频）
async function textToSpeech(text, refAudioBlob, promptText) {
  const formData = new FormData();
  formData.append('text', text);
  formData.append('text_language', 'zh');
  formData.append('ref_audio', refAudioBlob, 'ref.wav');
  formData.append('prompt_text', promptText || '');
  formData.append('prompt_language', 'zh');
  formData.append('how_to_cut', '凑四句一切');
  formData.append('top_k', '20');
  formData.append('top_p', '0.6');
  formData.append('temperature', '0.6');
  formData.append('speed', '1.0');
  formData.append('return_base64', 'true');

  const res = await fetch('http://localhost:40302/inference/tts', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

// 播放返回的音频
function playBase64Audio(base64Data) {
  const binaryStr = atob(base64Data);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  const audioCtx = new AudioContext();
  audioCtx.decodeAudioData(bytes.buffer, (buffer) => {
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);
    source.start();
  });
}

// 使用示例
async function main() {
  await loadModels('GPT_weights_v2Pro/my_role.ckpt', 'SoVITS_weights_v2Pro/my_role.pth');

  const result = await textToSpeech('你好，欢迎使用！', audioFile, '参考文本');
  if (result.success) {
    playBase64Audio(result.audio_data);
  }
}
```

### ASR 转录

```javascript
async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append('audio_file', audioBlob, 'speech.wav');
  formData.append('language', 'zh');
  formData.append('model_type', 'funasr');

  const res = await fetch('http://localhost:40302/inference/transcribe', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}
```

### 实时 ASR WebSocket

推荐对话场景使用 `/ws/asr/final`。它在 VAD 判断一句结束后返回最终文本，不发送实时中间字幕。

```javascript
async function startRealtimeAsr(pcmStream) {
  const ws = new WebSocket('ws://localhost:40302/ws/asr/final');
  ws.binaryType = 'arraybuffer';

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'result' && !data.is_interim) {
      console.log('最终段落:', data.text);
    }

    if (data.type === 'status' && data.final_text !== undefined) {
      console.log('完整文本:', data.final_text);
    }
  };

  await new Promise((resolve) => {
    ws.onopen = resolve;
  });

  ws.send(JSON.stringify({ command: 'start' }));

  // pcmStream 需要持续产出 16kHz / mono / signed int16 / little-endian 的 PCM 二进制帧。
  for await (const pcmChunk of pcmStream) {
    ws.send(pcmChunk);
  }

  ws.send(JSON.stringify({ command: 'stop' }));
}
```

实时接口只接收裸 PCM 二进制，不接收 mp3/wav/m4a 文件块。final 结果会由后端自动补标点。

如果需要边说边显示字幕，可以把地址换成 `ws://localhost:40302/ws/asr/transcribe`，它会额外返回 `is_interim=true` 的实时片段。

如果 WebSocket 握手返回 `403 Forbidden`，但 `GET /health` 和 `/docs` 正常，优先确认服务端已经部署最新后端代码并重启 PM2。当前版本的 `/ws/asr/final` 和 `/ws/asr/transcribe` 不做 token 鉴权、不限制 Origin；正确启动后握手日志应显示 `[accepted]`，连接成功后第一条消息为：

```json
{"type":"connection","status":"connected","message":"VAD final 识别已就绪"}
```

### 角色管理

```javascript
// 列出角色
async function listRoles() {
  const res = await fetch('http://localhost:40302/api/role/list/');
  return res.json();
}

// 导入角色
async function importRole(name, gptFile, sovFile, promptAudio) {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('world_id', '1');
  formData.append('version', 'v2Pro');
  formData.append('gpt_file', gptFile, 'model.ckpt');
  formData.append('sov_file', sovFile, 'model.pth');
  if (promptAudio) {
    formData.append('prompt_audio', promptAudio, 'ref.wav');
  }

  const res = await fetch('http://localhost:40302/api/role/import/', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}
```

### 健康检查

```javascript
async function healthCheck() {
  const res = await fetch('http://localhost:40302/health');
  const data = await res.json();
  console.log(`服务状态: ${data.gateway_status}`);
  console.log(`子服务: ${data.healthy_services}/${data.total_services} 正常`);
  return data;
}
```

---

## 附录：常见 HTTP 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| `200` | 成功 | 请求处理成功 |
| `400` | 参数错误 | 必填参数缺失或格式错误 |
| `401` | 未认证 | 启用了认证但未传或传错 API Key |
| `404` | 资源不存在 | 路径错误或训练任务不存在 |
| `408` | 超时 | 请求处理超时 |
| `429` | 频率限制 | 请求过于频繁 |
| `500` | 服务端错误 | 内部处理异常 |
| `503` | 服务不可用 | 子服务未加载或加载失败 |
