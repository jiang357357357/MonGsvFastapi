# 训练与模型

本文说明 Music 后端调用训练接口时需要了解的流程、默认值和当前实现限制。完整字段定义以 [API 完整手册](../01-接口协议/01-API完整手册.md) 为准。

## 1. 支持范围

当前支持以下 GPT-SoVITS 版本：

```text
v1 / v2 / v3 / v4 / v2Pro / v2ProPlus
```

- GPT 使用 `GPT_SoVITS/s1_train.py`。
- SoVITS V1/V2/V2Pro/V2ProPlus 使用 `GPT_SoVITS/s2_train.py`。
- SoVITS V3/V4 使用 `GPT_SoVITS/s2_train_v3_lora.py`。
- 官方训练配置模板保持不变；FastAPI 根据请求复制模板并写入项目工作区，不直接修改仓库模板。

## 2. 推荐训练链路

```text
原始音频
 -> 音频切片
 -> 离线 ASR 标注
 -> 文本特征提取
 -> 音频特征提取
 -> 语义编码
 -> 训练数据完整性检查
 -> SoVITS/GPT 顺序训练
 -> 模型权重目录
```

ASR 由后端按训练语言自动分流：中文使用 FunASR Paraformer-large + FSMN VAD +标点模型，粤语使用 FunASR UniASR 2-pass Cantonese，英语、日语、韩语等使用 Faster-Whisper large-v3。训练标注不使用实时 `paraformer-zh-streaming`。

推荐入口：

| 接口 | 用途 |
|------|------|
| `POST /workflow/complete` | 已有音频目录；可选择是否开始训练 |
| `POST /workflow/training/full` | 上传/准备音频并启动完整训练流程 |
| `GET /workflow/training/status/{workflow_id}` | 查询顺序训练工作流状态 |
| `POST /workflow/training/stop/{workflow_id}` | 停止排队中或运行中的完整训练工作流 |
| `POST /training/gpt/start` | 单独启动 GPT 训练 |
| `POST /training/sovits/start` | 单独启动 SoVITS 训练 |
| `GET /training/status/{job_id}` | 查询单个训练任务 |
| `POST /training/stop/{job_id}` | 停止单个训练任务 |

完整工作流会立即返回 `workflow_id`，训练在后台执行。调用方不应保持 HTTP 请求等待训练结束，而应轮询状态接口。

## 3. 顺序与失败处理

`training_order` 支持：

- `sovits_first`：默认，先 SoVITS 后 GPT。
- `gpt_first`：先 GPT 后 SoVITS。

当前实现保证：

1. 前一个目标状态为 `completed` 后，才启动下一个目标。
2. 前一个目标失败、停止或启动失败时，不再启动后续目标。
3. 完整训练工作流通过全局锁串行执行，同一时间只运行一个完整工作流。
4. 手动调用单项训练接口不受完整工作流锁限制。

工作流状态：

```text
queued -> running -> completed
                  -> failed
                  -> stopped
```

工作流记录目前只保存在网关进程内存中。后端重启后，历史 `workflow_id` 无法继续查询。

## 4. 当前默认值

### GPT

| 参数 | 默认值 |
|------|-------:|
| `version` | `v2Pro` |
| `batch_size` | 8 |
| `total_epoch` | 15 |
| `precision` | `16-mixed` |

V1 配置模板保留官方 `phoneme_vocab_size=512`；其他版本保留官方 `732`。只有显式传入 `phoneme_vocab_size` 时才覆盖模板值。

### SoVITS

| 参数 | 默认值 |
|------|-------:|
| `version` | `v2Pro` |
| `batch_size` | 32 |
| `total_epoch` | 8 |
| `segment_size` | 20480 |
| `fp16_run` | `true` |

`segment_size` 已写入实际读取的 `train.segment_size`。减小它可以降低显存占用，但会改变单个训练片段长度。

注意：FastAPI 默认批次大小是固定值，而官方 Gradio 会根据显存动态计算。对于 V3/V4，调用方不要直接沿用 `batch_size=32`；应根据显存显式设置较小值。远程约 32 GB 显存设备按官方策略计算时，V3/V4 的初始参考值约为 4。

## 5. 与官方训练脚本的差异

模型主体、损失函数和训练配置模板保持官方实现。运行层有以下兼容调整：

- GPT 单卡时不启用 DDP；多卡时继续使用 DDP。
- SoVITS 单卡直接在当前进程训练，不使用 `mp.spawn`/DDP。
- SoVITS 单卡 DataLoader 使用 `num_workers=0`，优先保证 Windows 和单卡稳定性；吞吐可能低于官方的多 worker 设置。
- GPT 保持官方手动优化方式；`ScaledAdam` 自带 `clipping_scale=2.0`，不向 Lightning Trainer 传入自动梯度裁剪参数。
- 增加 Windows/PosixPath checkpoint 安全加载兼容。
- 单进程模式下，采样器和 VQ codebook 不依赖已初始化的分布式进程组。

因此，当前训练权重格式仍兼容官方，但训练速度、数值轨迹和完全可复现性不保证与官方逐步一致。

## 6. 输出目录

完整工作流会把数据、checkpoint 和最终模型分别组织到项目工作区。业务调用方应优先使用接口响应中的实际路径，不要自行拼接：

```text
project_root
model_root
gpt_model_dir
sovits_model_dir
```

角色资源最终应包含：

```text
Resources/Model/<世界>/<角色>/<版本>/GPT/*.ckpt
Resources/Model/<世界>/<角色>/<版本>/SoVITS/*.pth
Resources/Model/<世界>/<角色>/<版本>/emotion/*.{wav,mp3,flac,...}
Resources/Model/<世界>/<角色>/<版本>/meta/role.json
```

训练完成后通过角色/模型资源接口刷新列表，不要假设最新文件名固定。
