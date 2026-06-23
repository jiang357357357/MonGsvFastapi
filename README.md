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
- FFmpeg shared 运行时
- 可选：`uv`（推荐）

Windows 下不要只放一个 `ffmpeg.exe`。  
当前项目的音频链路还需要 FFmpeg 的 shared DLL，推荐直接把完整包放到以下任一目录：

- `Tool/bin`
- `Tool/ffmpeg/bin`

至少需要包含：

- `ffmpeg.exe`
- `ffprobe.exe`
- `avcodec-*.dll`
- `avformat-*.dll`
- `avutil-*.dll`
- `swresample-*.dll`
- `swscale-*.dll`

项目启动时会自动把这两个目录注入运行时环境，不需要手动改系统 `PATH`。

可以用下面的命令提前自检：

```powershell
.venv\Scripts\python.exe -c "from Code.runtime_env import ensure_audio_runtime; ensure_audio_runtime(strict=True, verify_torchcodec=True, verbose=True)"
```

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

## 启动项目

Windows 下可以直接使用 `Script/Cmd/Win` 里的启动脚本：

```powershell
.\Script\Cmd\Win\start.cmd
```

开发模式：

```powershell
.\Script\Cmd\Win\start-dev.cmd
```

生产启动脚本会调用 `Code\Main\launch.py`，启动 FastAPI 网关，并用 Python 托管已有的前端 `dist`。
客户机器运行生产包不需要安装 Node.js、`npm` 或 `npx`；这些工具只在打包机重新构建前端时需要。

如果需要重新编译前端，先单独执行：

```powershell
.\Script\Cmd\Win\build-frontend.cmd
```

Linux 下对应脚本在 `Script/Cmd/Linux`：

```bash
bash Script/Cmd/Linux/start.sh
bash Script/Cmd/Linux/start-dev.sh
bash Script/Cmd/Linux/build-frontend.sh
```

## 给客户做离线 GPU 环境

这个仓库现在的 Python 环境特征是：

- Python：`3.10`
- PyTorch：当前本地锁定为 `2.11.0+cu128`
- `torch / torchaudio / torchvision`：来自 `CUDA 12.8` wheel 源

也就是说，**最适合这个项目的交付方式不是直接拷 `.venv`**，而是：

1. 你在开发机导出离线 wheel 包
2. 把仓库源码 + `Env/OfflinePy` 一起打给客户
3. 客户机器本地安装 `Python 3.10 x64`
4. 客户离线创建 `.venv` 并从本地 wheel 安装

这样比直接搬 `.venv` 更稳，尤其是 GPU 版 `torch`。

### 开发机导出离线包

先保证你自己的 `.venv` 已经能正常跑 GPU：

```powershell
.venv\Scripts\python.exe Env\PY\check_gpu.py
```

再导出离线环境：

```powershell
powershell -ExecutionPolicy Bypass -File Env\PY\export_offline.ps1
```

导出完成后会生成：

```text
Env/OfflinePy/
├─ wheels/                 # 所有离线 wheel 包
├─ requirements.lock.txt   # 从 uv.lock 导出的锁定依赖
├─ install_offline.ps1     # 客户离线安装脚本
├─ check_gpu.py            # 客户 GPU 自检脚本
└─ bundle-info.txt         # 当前打包机 Python / Torch / GPU 信息
```

### 客户机器离线安装

客户机器需要先满足：

- Windows x64
- Python `3.10.x`
- NVIDIA 驱动已正确安装
- 显卡驱动要能支持你当前交付的 `torch` CUDA 版本

然后在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File Env\OfflinePy\install_offline.ps1
```

安装完成后，脚本会自动打印：

- Python 版本
- `torch.__version__`
- `torch.version.cuda`
- `torch.cuda.is_available()`
- `nvidia-smi` 输出

### 客户机器手动检查 GPU

如果要单独复查，可以运行：

```powershell
.venv\Scripts\python.exe Env\OfflinePy\check_gpu.py
```

或者直接看驱动：

```powershell
nvidia-smi
```

### 这种方案适合什么，不适合什么

适合：

- 客户不能翻墙
- 客户机器可以安装 Python
- 你们当前就打算继续沿用 `uv + .venv + Windows` 这条链路

不适合：

- 客户机器完全不能装 Python
- 你想做到一份环境跨多种系统直接搬运
- 你们后面会频繁切 CUDA 大版本

如果后续要做更重的 GPU 交付，比如长期维护多台客户机、依赖持续增多、需要更强的环境可搬运性，再考虑 `conda-pack` 或 Docker。

### 项目打包

Windows 下统一使用 `Script/7Z/win/pack.ps1`：

```powershell
powershell -ExecutionPolicy Bypass -File .\Script\7Z\win\pack.ps1
```

打包脚本会先执行前端构建，并把 `Code/GptSov_Front/dist` 一起放进压缩包。  
如果只想复用已有 `dist`，可以跳过前端构建：

```powershell
powershell -ExecutionPolicy Bypass -File .\Script\7Z\win\pack.ps1 -SkipFrontendBuild
```

指定输出文件：

```powershell
powershell -ExecutionPolicy Bypass -File .\Script\7Z\win\pack.ps1 `
  -OutputFile "D:\code\model\mongsvfastapi\test\MonGsvFastapi.7z"
```

该脚本会读取 `.monconfig` 中 `[pack] EXCLUDE_PATTERNS` 的排除规则。

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

注意：

- `G2PWModel` 只是中文 G2PW 的模型数据
- `GPT_SoVITS/text/g2pw/` 这套 Python 源码必须跟仓库一起存在
- 缺少源码时，中文链路会在导入 `text.g2pw` 时直接失败

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
- `GPT_SoVITS/text/g2pw/` 源码目录缺失，但你在跑中文流程
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
