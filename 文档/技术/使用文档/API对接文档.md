# MonGSV API 对接文档

## 概述

MonGSV 提供 HTTP REST API 接口，支持跨域调用，可被其他项目直接集成使用。

- **基础 URL**: `http://localhost:7020/api/`
- **跨域支持**: 已启用 CORS，允许所有来源访问
- **Content-Type**: `application/json`

---

## 快速开始

### 1. 环境准备

确保 MonGSV 后端服务已启动：

```bash
# 默认端口 7020
cd /home/ubuntu/work/MonGsvCore
python Code/GsvBack/main.py
```

### 2. 基础调用示例

```python
import requests

BASE_URL = "http://localhost:7020/api"

# 测试连接
response = requests.get(f"{BASE_URL}/models/list/")
print(response.json())
```

---

## 标准调用流程

MonGSV 已支持**自动启动推理服务**，对接方只需按以下顺序调用：

```
1. 获取版本列表 → GET /api/models/versions/from-enum/
                      ↓ 选择版本（如 v2ProPlus）
2. 获取世界列表 → GET /api/world/list/
                      ↓ 选择世界（如 Default, Arknights）
3. 获取角色列表 → GET /api/models/info/characters/?version=xxx&world=xxx
                      ↓ 选择角色（如 特蕾西娅）
4. 获取情感列表 → GET /api/emotions/list/?version=xxx&character=xxx
                      ↓ 选择情感（如 温柔）
5. 执行语音合成 → POST /api/music/inference/tts/synthesize/
                      ↓
                    内部自动启动推理服务（无需手动调用）
```

**说明**：
- **版本**和**世界**是独立的，没有强关联
- 获取世界列表不需要传版本参数（可选，传了只会筛选有该版本角色的世界）
- 获取角色时需要传入**版本+世界**两个参数
- 语音合成接口内部会自动检查并启动推理服务

---

## API 接口列表

### 一、模型管理接口

#### 1. 获取模型列表

**接口**: `GET /api/models/list/`

**响应**:
```json
{
  "success": true,
  "message": "获取模型列表成功",
  "sovits_models": ["model1.pth", "model2.pth"],
  "gpt_models": ["model1.ckpt", "model2.ckpt"]
}
```

---

#### 2. 刷新模型列表

**接口**: `POST /api/models/refresh/`

**响应**:
```json
{
  "success": true,
  "message": "模型列表已刷新"
}
```

---

#### 3. 获取版本列表

**接口**: `GET /api/models/versions/from-enum/`

**说明**: 获取系统支持的所有版本（如 v2ProPlus、v3 等）

**响应**:
```json
{
  "success": true,
  "message": "获取版本列表成功",
  "versions": ["v2ProPlus", "v3"]
}
```

---

#### 4. 获取世界列表

**接口**: `GET /api/world/list/`

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| version | string | 否 | 版本名称，用于筛选拥有该版本角色的世界（可选） |

**注意**：世界和版本是独立的，不传 version 参数会返回所有世界

**响应**:
```json
{
  "success": true,
  "message": "获取世界列表成功",
  "version": "v2ProPlus",
  "worlds": [
    {"id": 1, "name": "Default", "description": "默认世界"},
    {"id": 2, "name": "Arknights", "description": "明日方舟"}
  ],
  "count": 2
}
```

---

#### 5. 获取角色列表

**接口**: `GET /api/models/info/characters/`

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| version | string | 是 | 版本名称，如 "v2ProPlus" |
| world | string | 否 | 世界/作品名称，默认 "Default" |

**响应**:
```json
{
  "success": true,
  "message": "获取角色列表成功",
  "version": "v2ProPlus",
  "characters": ["特蕾西娅", "阿米娅", "凯尔希"],
  "count": 3
}
```

---

### 二、情感模块接口

#### 1. 获取情感列表

**接口**: `GET /api/emotions/list/`

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| version | string | 是 | 版本名称 |
| character | string | 是 | 角色名称 |

**响应**:
```json
{
  "success": true,
  "message": "获取情感列表成功",
  "emotions": ["温柔", "平常", "开心", "悲伤"]
}
```

---

#### 2. 获取所有角色情感

**接口**: `GET /api/emotions/all/`

**响应**:
```json
{
  "success": true,
  "message": "获取所有情感成功",
  "data": {
    "特蕾西娅": ["温柔", "平常"],
    "阿米娅": ["开心", "悲伤"]
  }
}
```

---

### 三、TTS 推理接口

#### 1. 获取支持的语言列表

**接口**: `GET /api/music/inference/reference_text_languages/`

**响应**:
```json
["中文", "英文", "日文", "粤语", "韩文", "中英混合", "日英混合", "粤英混合", "韩英混合", "多语种混合", "多语种混合(粤语)"]
```

---

#### 2. 启动/切换 TTS 推理服务

**接口**: `POST /api/music/inference/tts/change/`

**说明**: **必须先调用此接口启动推理服务，才能进行语音合成**

**请求体**:
```json
{
  "version": "v2ProPlus",
  "world": "Default",
  "character": "特蕾西娅",
  "gpu_number": "0",
  "batched_infer_enabled": false
}
```

**参数说明**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| version | string | 是 | 版本名称（如 v2ProPlus） |
| world | string | 否 | 世界/作品名称，默认 "Default" |
| character | string | 是 | 角色名称 |
| gpu_number | string | 是 | GPU 卡号，如 "0" |
| batched_infer_enabled | boolean | 否 | 是否启用并行推理，默认 false |

**响应**:
```json
{
  "status": "opened",
  "message": "推理服务已开启",
  "visible": true
}
```

---

#### 3. 获取推理服务状态

**接口**: `GET /api/music/inference/tts/status/`

**响应**:
```json
{
  "status": "opened",
  "message": "推理服务运行中",
  "visible": true
}
```

---

#### 4. 执行 TTS 语音合成

**接口**: `POST /api/music/inference/tts/synthesize/`

**说明**: **必须先启动推理服务，否则合成会失败**

**请求体**:
```json
{
  "text": "你好，前辈！我是林晚晴。",
  "text_language": "中文",
  "version": "v2ProPlus",
  "world": "Default",
  "character": "特蕾西娅",
  "emotion": "温柔",
  "speed": 1.0,
  "top_k": 15,
  "top_p": 1.0,
  "temperature": 1.0
}
```

**参数说明**:

**必需参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| text | string | 要合成的文本 |
| text_language | string | 文本语言（中文/英文/日文/粤语/韩文/中英混合/日英混合/粤英混合/韩英混合/多语种混合/多语种混合(粤语)） |
| version | string | 版本名称（如 v2ProPlus） |
| character | string | 角色名称 |
| emotion | string | 情感名称 |

**可选参数**:
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| world | string | "Default" | 世界/作品名称 |
| speed | float | 1.0 | 语速，范围 0.5-2.0 |
| top_k | int | 15 | Top-K 采样参数 |
| top_p | float | 1.0 | Top-P 采样参数 |
| temperature | float | 1.0 | 温度参数 |
| sample_steps | int | 32 | 采样步数（仅 V3 模型） |
| how_to_cut | string | "凑四句一切" | 文本切分方式 |
| pause_second | float | 0.3 | 句间停顿秒数 |
| gpu_number | string | "0" | GPU 卡号 |
| batched_infer_enabled | boolean | false | 是否启用并行推理 |
| if_sr | boolean | false | 是否启用超分辨率 |
| ref_free | boolean | false | 无参考文本模式 |
| if_freeze | boolean | false | 是否直接对上次合成结果调整语速和音色 |
| prompt_text | string | null | 覆盖情感参考文本 |
| inp_refs | array | null | 辅助参考音频路径列表 |

**响应**: 音频文件流 (audio/wav)

---

## 完整调用流程示例

### Python 完整示例

```python
import requests
import json

BASE_URL = "http://localhost:7020/api"

class MonGsvClient:
    def __init__(self, base_url="http://localhost:7020"):
        self.base_url = base_url
        self.current_version = None
        self.current_character = None
    
    def get_versions(self):
        """获取版本列表"""
        response = requests.get(f"{self.base_url}/api/models/versions/from-enum/")
        return response.json()
    
    def get_worlds(self, version=None):
        """获取世界列表"""
        params = {}
        if version:
            params["version"] = version
        response = requests.get(
            f"{self.base_url}/api/world/list/",
            params=params
        )
        return response.json()
    
    def get_characters(self, version, world="Default"):
        """获取角色列表"""
        response = requests.get(
            f"{self.base_url}/api/models/info/characters/",
            params={"version": version, "world": world}
        )
        return response.json()
    
    def get_emotions(self, version, character):
        """获取情感列表"""
        response = requests.get(
            f"{self.base_url}/api/emotions/list/",
            params={"version": version, "character": character}
        )
        return response.json()
    
    def start_inference(self, version, character, world="Default", gpu_number="0"):
        """启动推理服务"""
        response = requests.post(
            f"{self.base_url}/api/music/inference/tts/change/",
            json={
                "version": version,
                "world": world,
                "character": character,
                "gpu_number": gpu_number,
                "batched_infer_enabled": False
            }
        )
        result = response.json()
        if result.get("status") == "opened":
            self.current_version = version
            self.current_character = character
        return result
    
    def synthesize(self, text, character, emotion, version="v2ProPlus", 
                   world="Default", language="中文", speed=1.0, **kwargs):
        """语音合成（自动启动推理服务）"""
        data = {
            "text": text,
            "text_language": language,
            "version": version,
            "world": world,
            "character": character,
            "emotion": emotion,
            "speed": speed,
            "top_k": kwargs.get("top_k", 15),
            "top_p": kwargs.get("top_p", 1.0),
            "temperature": kwargs.get("temperature", 1.0)
        }
        
        response = requests.post(
            f"{self.base_url}/api/music/inference/tts/synthesize/",
            json=data
        )
        return response.content  # 返回音频数据


# ============ 使用示例 ============

client = MonGsvClient()

# 1. 获取可用版本
versions = client.get_versions()
print(f"可用版本: {versions}")
# 输出: {'versions': ['v2ProPlus', 'v3'], ...}

# 2. 获取世界列表（世界和版本是独立的）
worlds = client.get_worlds()
print(f"可用世界: {worlds}")
# 输出: {'worlds': [{'name': 'Default'}, {'name': 'Arknights'}], ...}

# 3. 选择世界并获取角色列表
world = "Arknights"
characters = client.get_characters(version, world)
print(f"可用角色: {characters}")
# 输出: {'characters': ['特蕾西娅', '阿米娅', ...], ...}

# 4. 选择角色并获取情感列表
character = "特蕾西娅"
emotions = client.get_emotions(version, character)
print(f"可用情感: {emotions}")
# 输出: {'emotions': ['温柔', '平常', '开心', ...], ...}

# 5. 直接执行语音合成（自动启动推理服务）
audio_data = client.synthesize(
    text="你好，前辈！我是林晚晴。",
    character=character,
    emotion="温柔",
    version=version,
    world=world,
    language="中文",
    speed=1.0
)

# 保存音频
with open("output.wav", "wb") as f:
    f.write(audio_data)
print("音频已保存到 output.wav")
```

---

## 其他接口

### 角色管理

- `GET /api/role/list/` - 获取角色列表（另一个接口）

### 世界观

- `GET /api/world/` - 世界观接口

### GPT/SoVITS 数据

- `GET /api/gpt/` - GPT 相关接口
- `GET /api/sov/` - SoVITS 相关接口

---

## 错误处理

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "message": "错误描述信息"
}
```

---

## 注意事项

1. **自动启动**: 语音合成接口已内置自动启动推理服务功能，无需手动管理
2. **获取资源顺序**: 版本 → 角色 → 情感，按此顺序获取
3. **GPU 显存**: 确保 GPU 有足够的显存（建议 4GB 以上）
4. **模型切换**: 切换角色或版本时，系统会自动重新加载模型
5. **并发限制**: 目前不支持多并发请求，建议串行调用

---

## 相关文档

- 项目地址: `/home/ubuntu/work/MonGsvCore`
- 后端服务: `Code/GsvBack/main.py`
- 环境配置: `Env/.env`
