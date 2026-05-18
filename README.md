# MonGsvFastapi

这个 `README.md` 只说明**当前这个仓库**怎么安装、启动和使用。

它不是上游 `GPT-SoVITS` 的通用说明书。  
当前项目的推荐主入口是：

- 后端：`Code/FastApi/Main/run_gateway.py`
- 前端：`Code/GptSov_Front`

## 这个项目能做什么

这套仓库把 GPT-SoVITS 的几个常见环节整合成了一套前后端控制台：

- 语音合成
- 角色 / 世界 / 模型资源管理
- 情感参考音频管理
- 数据预处理
- GPT / SoVITS 训练
- 统一 FastAPI 网关
- 前端调试页和后端接口联调

## 仓库结构

```text
MonGsvFastapi/
├─ Code/
│  ├─ FastApi/                  # FastAPI 网关与各模块服务
│  └─ GptSov_Front/             # Vite + React 前端
├─ Env/
│  ├─ UV/                       # UV 安装脚本
│  ├─ PY/                       # Python 虚拟环境安装脚本
│  └─ Models/DownList/          # 共享模型下载/安装/检查脚本
├─ GPT_SoVITS/                  # GPT-SoVITS 本体代码
├─ Resources/
│  ├─ Model/                    # 角色成品模型
│  └─ Train/                    # 训练工程与中间产物
├─ tools/                       # ASR / UVR5 等工具
├─ .monconfig                   # 端口、路径、日志等主配置
└─ pyproject.toml               # Python 依赖定义
```

补充文档：

- [共享模型下载说明](Env/Models/DownList/README.md)
- [Resources 目录规范](Resources/README.md)
- [网关运维脚本说明](Code/FastApi/Tool/README.md)

## 运行前准备

下面的示例命令以 **Windows PowerShell** 为主，因为仓库内现成脚本主要是 `ps1`。

### 必备工具

- Python 3.10
- Node.js
- FFmpeg
- 可选：`uv`（推荐）

确认 `ffmpeg` 和 `ffprobe` 已经在 `PATH` 里，音频切分、转码、训练预处理都会用到它们。

### 关于 Python 依赖

当前 [`pyproject.toml`](pyproject.toml) 默认把：

- `torch`
- `torchaudio`
- `torchvision`

指向了 `CUDA 12.8` 的索引源。

如果你的机器不是这个环境，建议先检查并按需调整 `pyproject.toml` 里的 `[[tool.uv.index]]` 和 `[tool.uv.sources]`，再执行依赖安装。

## 安装依赖

### 方式一：使用仓库自带脚本

先安装 `uv`：

```powershell
powershell -ExecutionPolicy Bypass -File Env\UV\install.ps1
```

再创建 `.venv` 并安装 Python 依赖：

```powershell
powershell -ExecutionPolicy Bypass -File Env\PY\install.ps1
```

安装前端依赖：

```powershell
cd Code\GptSov_Front
npm install
```

### 方式二：手动安装

```powershell
uv venv .venv
.venv\Scripts\activate
uv sync --link-mode=copy
```

然后安装前端依赖：

```powershell
cd Code\GptSov_Front
npm install
```

## 准备模型

项目分两类模型：

### 1. 共享依赖模型

位置和说明都在：

- [Env/Models/DownList/README.md](Env/Models/DownList/README.md)

最小必需通常是：

- `PretrainedModels`
- `G2PWModel`（如果要做中文）

按功能选装：

- `FunASRModels`
- `FasterWhisperModels`
- `UVR5Weights`

检查示例：

```powershell
python Env/Models/DownList/PretrainedModels/check.py
python Env/Models/DownList/G2PWModel/check.py
python Env/Models/DownList/FunASRModels/check.py
python Env/Models/DownList/FasterWhisperModels/check.py
python Env/Models/DownList/UVR5Weights/check.py
```

### 2. 你自己的角色模型

这部分不在 `DownList` 里，通常放在：

- `Resources/Model/<world>/<role>/<base_version>/...`

角色成品至少要有：

- GPT 权重：`*.ckpt`
- SoVITS 权重：`*.pth`

如果你是“直接拿现成角色模型来合成”，只要把共享依赖和角色权重都准备好，就可以开始用。

### 可选：用 `Env/.env` 覆盖模型路径

如果你不想使用默认目录，可以在 `Env/.env` 里设置这些变量：

```env
HF_ENDPOINT=https://hf-mirror.com
PRETRAINED_MODELS_PATH=GPT_SoVITS/pretrained_models
G2PW_MODEL_PATH=GPT_SoVITS/text/G2PWModel
FUNASR_MODELS_PATH=tools/asr/models
FASTER_WHISPER_MODELS_PATH=tools/asr/models
UVR5_WEIGHTS_PATH=tools/uvr5/uvr5_weights
```

没有这个文件也可以正常运行，默认会用仓库内的标准路径。

## 启动项目

### 后端

当前推荐统一从这里启动：

```powershell
.venv\Scripts\activate
python Code/FastApi/Main/run_gateway.py
```

常用参数：

```powershell
python Code/FastApi/Main/run_gateway.py --reload --log-level debug
python Code/FastApi/Main/run_gateway.py --host 0.0.0.0 --port 40302
python Code/FastApi/Main/run_gateway.py --enable-auth --api-key your-secret
```

当前 `.monconfig` 默认端口：

- 后端：`40302`

启动后可访问：

- OpenAPI 文档：`http://127.0.0.1:40302/docs`
- 健康检查：`http://127.0.0.1:40302/health`

运维命令：

```powershell
python Code/FastApi/Main/run_gateway.py status
python Code/FastApi/Main/run_gateway.py stop
python Code/FastApi/Main/run_gateway.py cleanup
```

PowerShell 脚本版也可以直接用：

```powershell
.\Code\FastApi\Tool\status_gateway.ps1
.\Code\FastApi\Tool\stop_gateway.ps1
.\Code\FastApi\Tool\cleanup_gateway.ps1
```

### 前端

```powershell
cd Code\GptSov_Front
npm run dev
```

当前 `.monconfig` 默认端口：

- 前端：`40031`

打开：

- `http://127.0.0.1:40031`

前端默认把后端地址理解为 `localhost:40302`。  
如果你修改了后端端口或部署到别的机器，请在前端的“系统设置”页里改成正确地址。

## 先怎么用，再怎么用

### 场景 A：我已经有角色模型，只想合成

建议顺序：

1. 安装 Python / Node / FFmpeg 依赖
2. 准备共享模型，至少补齐 `PretrainedModels`
3. 如果要合成中文，再补 `G2PWModel`
4. 启动后端
5. 启动前端
6. 打开“资源管理”，导入角色的 `GPT` / `SoVITS` 权重和参考音频
7. 打开“语音合成”，选择版本、角色、模型并加载
8. 填入目标文本，执行合成

### 场景 B：我要从原始音频开始训练角色

建议顺序：

1. 安装基础依赖
2. 准备共享模型
3. 如果做中文训练，建议补齐：
   - `PretrainedModels`
   - `G2PWModel`
   - `FunASRModels`
4. 如果做英文 / 日文 / 多语训练，建议补齐：
   - `PretrainedModels`
   - `FasterWhisperModels`
5. 如果训练前要做人声分离或去混响，再补 `UVR5Weights`
6. 启动后端和前端
7. 打开“模型训练”页，选择：
   - 版本
   - 世界
   - 角色名
   - 输入音频目录 / 输出目录
   - 训练目标和批大小、轮数
8. 上传原始音频或指定已有目录
9. 启动完整训练流程
10. 训练完成后，到“资源管理”或“语音合成”页查看和使用产出

## 前端页面怎么分工

| 页面 | 用途 |
| --- | --- |
| `语音合成` | 加载 GPT / SoVITS 模型，提交参考音频与文本，执行 TTS |
| `模型训练` | 触发预处理、特征提取、GPT / SoVITS 训练，并轮询训练状态 |
| `情感配置` | 为角色维护情感标签、参考文本和参考音频 |
| `资源管理` | 管理世界、角色，导入角色模型，查看资源目录结果 |
| `后端测试` | 直接调网关接口，适合联调和排错 |
| `系统设置` | 修改前端连接的后端地址等本地配置 |

## 常用 API

启动后端后，可以直接用 `/docs` 调接口。几个高频入口如下：

- `GET /health`
- `GET /services/status`
- `GET /api/world/list/`
- `GET /api/role/list/`
- `GET /api/role/workspace/list/`
- `POST /api/role/import/`
- `POST /inference/models/load`
- `POST /inference/tts`
- `POST /workflow/training/full`
- `GET /training/status/{job_id}`

简单健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:40302/health
```

## 关键目录说明

### `Resources/Model`

这里放角色成品模型，适合：

- 推理
- 发布
- 情感参考
- 已训练完成的 GPT / SoVITS 权重

### `Resources/Train`

这里放训练工程和过程文件，适合：

- 原始音频
- 切分结果
- ASR 结果
- 特征文件
- 训练日志
- checkpoint

更细的目录约定见：

- [Resources/README.md](Resources/README.md)

## 配置文件

### `.monconfig`

这里控制：

- 后端端口
- 前端端口
- 模型 / 输出 / 临时目录
- 日志路径
- GPU 和 half precision 开关

当前默认值里比较重要的是：

- 后端端口：`40302`
- 前端端口：`40031`

### `Env/.env`

这是可选覆盖层，适合放：

- HuggingFace 镜像地址
- 共享模型自定义路径

## 常见问题

### 1. 后端启动了，但前端连不上

先检查：

- 后端是否真的在 `40302` 监听
- 前端“系统设置”里的后端地址是否仍是 `localhost:40302`
- 是否改过 `.monconfig` 端口但前端没有同步

### 2. 接口报模型缺失

先跑检查脚本：

```powershell
python Env/Models/DownList/PretrainedModels/check.py
python Env/Models/DownList/G2PWModel/check.py
```

如果是训练相关报错，再补查：

```powershell
python Env/Models/DownList/FunASRModels/check.py
python Env/Models/DownList/FasterWhisperModels/check.py
python Env/Models/DownList/UVR5Weights/check.py
```

### 3. 网关端口被占用

用这个：

```powershell
python Code/FastApi/Main/run_gateway.py stop
```

或者连临时目录一起清：

```powershell
python Code/FastApi/Main/run_gateway.py cleanup
```

### 4. 训练页能打开，但跑不动

通常先查这几件事：

- 共享模型没装全
- `ffmpeg` 不在 `PATH`
- GPU / Torch 版本和当前机器不匹配
- 输出目录没有写权限
- 训练输入目录为空

## 一句话开始

如果你只想最快把项目跑起来，可以按这个顺序：

1. 安装 `uv`
2. 跑 `Env\PY\install.ps1`
3. 跑共享模型检查并补齐 `PretrainedModels`
4. 启动后端 `python Code/FastApi/Main/run_gateway.py`
5. 启动前端 `cd Code\GptSov_Front && npm run dev`
6. 打开前端先用“资源管理”导入角色，再去“语音合成”
