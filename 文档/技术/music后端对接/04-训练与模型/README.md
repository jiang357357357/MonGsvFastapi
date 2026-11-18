# 训练与模型

核对日期：2026-10-24。本文描述当前 FastAPI 后端，字段以 [API 完整手册](../01-接口协议/01-API完整手册.md) 和运行实例的 `/docs` 为准。

## 1. 支持范围与官方基线

支持版本：`v1`、`v2`、`v2Pro`、`v2ProPlus`、`v3`、`v4`、`v5dev`、`v5turbo`。

- GPT 调用 `GPT_SoVITS/s1_train.py`。
- SoVITS V1/V2/Pro 系列调用 `GPT_SoVITS/s2_train.py`；V3/V4/V5 调用 `GPT_SoVITS/s2_train_v3_lora.py`。
- V3/V4/V5 使用 LoRA；V5 由脚本选择 V5 生成器，不要求旧版判别器底模。
- GPT 的 V1、V2 使用各自底模，其余版本默认使用 `s1v3.ckpt`。
- V5 推理还需要匹配的 `gsv-v5-pretrained/s2Gv5dev.pth` 或 `s2Gv5turbo.pth`，以及 `gsv-v5-pretrained/vocoder.pth`。

本地内核合并基线为官方 `1b47ca07ef43a284e0b8bd7f29d3e1e3ff76082a`。本次对照的官方 `main` 为 `b4570b8`，其中新增的语义流式能力尚未合入本后端，不能直接照搬最新官方 `api_v2.py` 参数。

## 2. 推荐入口：训练工作台

新对接优先使用 `/training/workbench`，支持独立重训、显式续训、历史记录、日志、Loss 曲线及试听。

| 方法与路径 | 用途 |
|------------|------|
| `GET /training/workbench/defaults` | 获取当前硬件上的八版本训练默认值 |
| `GET /training/workbench/workspaces?world_name=...&project_name=...` | 查询缓存特征与可续训工作区 |
| `POST /training/workbench/start` | multipart 表单提交 `options` JSON 字符串和可选 `audio_files` |
| `GET /training/workbench/runs` | 获取最近最多 100 条历史记录 |
| `GET /training/workbench/runs/{workflow_id}` | 查询完整状态和训练指标 |
| `POST /training/workbench/runs/{workflow_id}/stop` | 请求停止任务 |
| `GET /training/workbench/runs/{workflow_id}/logs?target=sovits` | 获取日志尾部；`target` 也可为 `gpt` |
| `POST /training/workbench/runs/{workflow_id}/preview` | 训练完成后试听；JSON 为 `text`、`emotion`、可选 `seed`（默认 2027） |

`options` 字段及示例见 API 手册的“模型训练”。未知 `options` 字段会被拒绝。工作台要求可用 CUDA GPU，`world_name`、`project_name`、`version` 必填。`role_mode=new` 用于新角色，`existing` 用于已有角色的新版本或复训。至少选择 `train_gpt`、`train_sovits` 中一项，两项默认均为 `true`。

### 数据与训练方式

| 字段 | 值 | 行为 |
|------|----|------|
| `preprocessing_mode` | `full` | 原始音频切片、ASR、文本特征、音频特征、语义编码 |
| `preprocessing_mode` | `existing` | 使用切片目录 `input_audio_dir` 和标注 `list_file`，重新提取特征 |
| `preprocessing_mode` | `cached`（默认） | 复用 `source_version` / `source_workspace` 特征，不复制旧 checkpoint |
| `training_mode` | `fresh`（默认） | 为本次训练创建独立 `runs/<workflow_id>` 目录 |
| `training_mode` | `resume` | 使用 `resume_workspace` 中的 checkpoint，跳过预处理 |

缓存来源必须属于当前角色与所选数据版本；V1 与其他版本的文本特征不允许直接混用。跨版本复用时会按目标版本重新生成语义编码。

续训校验工作区归属、模型版本、SoVITS LoRA rank 和已完成轮数。总轮数表示累计目标，必须大于已完成轮数。停止预处理时，当前阶段可能要到阶段边界才退出。

### 状态与持久化

提交返回 `training_workflow.workflow_id`，随后轮询 `/training/workbench/runs/{workflow_id}`。状态包括 `queued`、`running`、`completed`、`failed`、`stopped`、`interrupted`。

记录写入 `Data/Training/workflows/*.json`。重启后保留历史，把未结束记录标为 `interrupted`；不会自动继续训练，需要显式选择 checkpoint 续训。

工作台与旧完整训练工作流共用全局锁，串行执行；前一个目标成功后才启动下一个目标。单项 `/training/gpt/start`、`/training/sovits/start` 不受此锁限制，调用方需自行协调 GPU。普通 TTS 也未接入全局 GPU 调度；工作台试听会在训练占用锁时返回 409。

## 3. 默认值与保存策略

调用 `GET /training/workbench/defaults` 获取实际默认值，避免在业务端固定 Batch。

| 参数 | V1/V2/V2Pro/V2ProPlus | V3/V4/V5dev/V5turbo |
|------|---------------------|-------------------|
| GPT 总轮数 | 15 | 15 |
| SoVITS 总轮数 | 8 | 2 |
| GPT 学习率 | 0.01 | 0.01 |
| SoVITS 学习率 | 0.0001 | 0.0001 |
| LoRA rank | 不用于此训练方式 | 32 |
| 梯度检查点 | 默认关闭 | 默认关闭 |
| Step 日志间隔 | 100 | 100 |
| 权重与恢复 checkpoint 保存间隔 | 各阶段最后一轮 | 各阶段最后一轮 |

GPU 默认 GPT Batch 按最小设备显存除以 2 计算；SoVITS 普通版本除以 2，LoRA 版本除以 8，结果至少为 1。精度按设备能力选择；实际生成配置在 FP32 时还会把 Batch 减半，至少保留 1。多卡默认值与所选 GPU 的可用性仍需调用方核对。

`save_every_epoch`、`gpt_save_every_epoch`、`sovits_save_every_epoch` 是兼容字段，服务端会覆盖为对应总轮数。官方 WebUI 默认 GPT 每 5 轮保存、普通 SoVITS 每 4 轮保存、LoRA SoVITS 每轮保存；本项目采用最终轮次保存。

新训练若在最后一轮前停止，可能没有可恢复的 checkpoint；续训中途停止也不会自动保存本次新增进度。不要把 `if_save_latest` 理解为每一步都在保存。

V1 GPT 模板保留 `phoneme_vocab_size=512`，其余版本保留 `732`。SoVITS `segment_size` 默认为 20480。日志和每轮 Loss 统计独立于保存频率，不会为缺失轮次补造 Loss。

## 4. 数据准备与当前限制

中文训练标注默认使用 `FunAudioLLM/Fun-ASR-Nano-2512` + FSMN VAD。Nano 固定修订为 `272c57b82523ada6fd87095e955f8e29100979ab`，存放于 `tools/asr/models/Fun-ASR-Nano-2512`，依赖 FunASR >= 1.4.1 的内置实现。本地文件完整时直接加载，缺失时下载固定修订。粤语使用 UniASR，其他支持语言使用 Faster-Whisper large-v3。已有标注不自动重写。

当前已知限制：工作流文本特征阶段未传目标版本，实际按默认 V2 清洗文本，V1 路径尚未与官方对齐。需要严格复现 V1 特征时，应先使用匹配版本的官方脚本生成特征，再按同版本 `cached` 流程训练；本次文档更新未修复该代码问题。

GPT 启动服务还要求文本和语义标注各至少 10 条；官方界面的检查不采用相同的十条门槛。

## 5. 与官方运行层的差异

主要训练目标、损失和导出格式沿用官方实现。当前封装增加以下运行行为：

- GPT 单卡不启用 DDP，多卡继续使用 DDP；官方 SoVITS 本身也已有单卡直训路径。
- 工作台启动 GPT 时设置 `num_workers=0`，SoVITS 单卡默认也使用 0 worker；与官方多 worker 配置不同。
- 增加 checkpoint 路径兼容、分布式初始化检查和数据前置校验。
- SoVITS 增加每轮平均 Loss，保留原始 Step 日志；比较曲线时应区分均值与采样点。

本次对照验证了配置生成和参数映射，未开展相同数据、相同随机种子的 GPU 训练 A/B 测试，不能据此承诺训练速度、音质或逐步数值完全一致。

## 6. 旧工作流与单项接口

`/workflow/complete`、`/workflow/training/full`、`/workflow/training/status/{workflow_id}`、`/workflow/training/stop/{workflow_id}` 继续保留。它们完成预处理后才返回训练排队结果，预处理期间 HTTP 请求仍在执行；旧工作流记录只在内存中，重启后不能继续查询。

旧接口的 ID 使用旧状态路径；工作台的 ID 使用 `/training/workbench/runs/{workflow_id}`。两组查询与停止路径不可互换。

单项 `/training/gpt/start`、`/training/sovits/start` 只接收 `exp_name`、`exp_root`、`workspace_dir`、`model_output_dir`、`version`、`batch_size`、`total_epoch` 表单字段。调学习率、GPU 编号或 LoRA rank 请用工作台 `options`；不要把 SDK 配置字段视为这些单项 HTTP 接口都已接入。

## 7. 输出目录

工作台新训练的目录结构：

```text
Resources/Train/Projects/<世界>/<角色>/<版本>/runs/<workflow_id>/
├── source/                 # 原始或切分音频
├── dataset/                # 文本、音频及语义特征
├── train/gpt/ckpt/          # GPT 恢复 checkpoint
├── train/sovits/            # SoVITS 日志
├── export/GPT/              # 本次导出 GPT 权重
├── export/SoVITS/           # 本次导出 SoVITS 权重
└── preview/                # 试听 WAV
```

SoVITS 恢复 checkpoint 位于工作区 `dataset/logs_s2_<版本>[_lora_<rank>]/G_*.pth`。默认 `publish_models=true` 会将最终权重复制到 `Resources/Model/<世界>/<角色>/<版本>/GPT`、`SoVITS`，并更新角色元数据。应读取接口返回的路径与 `preview`，不要自行拼接或假设固定文件名。
