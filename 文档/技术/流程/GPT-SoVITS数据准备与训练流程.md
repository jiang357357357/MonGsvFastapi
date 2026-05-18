# GPT-SoVITS 数据准备与训练完整流程

## 概览

```
原始音频
  ↓ [可选] 0a. UVR5 人声分离
  ↓ [可选] 0b. 语音切分
  ↓ [必需] 0c. ASR 语音识别
  ↓ [推荐] 0d. 文本校对
  ↓ [必需] 1A. 训练集格式化（三步特征提取）
  ↓ [必需] 1B. 模型训练（SoVITS + GPT）
  ↓         1C. 推理测试
```

---

## 第零阶段：数据准备

### 0a. UVR5 人声分离（可选）

**何时需要**：原始音频包含背景音乐、混响、伴奏时使用。

- 工具：`tools/uvr5/webui.py`
- 输入：带伴奏的音频文件
- 输出：纯人声 `.wav`
- 启动方式：webui 中点击"开启人声分离WebUI"按钮

---

### 0b. 语音切分（视情况而定）

**何时需要**：

| 情况 | 是否需要切分 |
|------|------------|
| 原始音频为长录音（>30秒） | ✅ 必须 |
| 原始音频为连续对话 | ✅ 必须 |
| 已有 2-15 秒的短片段 | ❌ 可跳过 |
| 录音室逐句录制 | ❌ 可跳过 |

**工具**：`tools/slice_audio.py`

**关键参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| threshold | -34 dB | 低于此音量视为静音切割点，越小切得越碎 |
| min_length | 4000 ms | 每段最短 4 秒，防止切出过短片段 |
| min_interval | 300 ms | 最短切割间隔 |
| hop_size | 10 ms | 音量检测精度 |
| max_sil_kept | 500 ms | 句首句尾保留的静音长度 |

**输出文件命名规则**：
```
原文件名_起始帧数_结束帧数.wav
例：interview.wav_0000000000_0000128000.wav
```

> 采样率为 32000 Hz，帧数 128000 = 4 秒

---

### 0c. ASR 语音识别（必需）

**作用**：自动识别切分后的音频内容，生成 `.list` 标注文件。

**工具**：`tools/asr/`（支持多种模型）

**支持的 ASR 模型**：

| 模型 | 语言 | 精度 |
|------|------|------|
| 达摩 ASR | 中文、粤语 | float32 |
| Faster Whisper | 多语种 | float16 / int8 |

**输出格式**（`.list` 文件）：
```
音频文件路径|说话人名|语言|文本内容
/path/to/001.wav|speaker|zh|你好，这是一段测试音频。
/path/to/002.wav|speaker|zh|今天天气很好。
```

---

### 0d. 文本校对（推荐）

**作用**：人工修正 ASR 识别错误，提升训练数据质量。

**工具**：`tools/subfix_webui.py`

- 输入：`.list` 标注文件
- 操作：在 WebUI 中逐条播放音频并修正文本
- 输出：修正后的 `.list` 文件

---

## 第一阶段：训练集格式化

### 1A. 三步特征提取

三步可以单独执行，也可以使用**一键三连**按钮自动串联执行。

---

#### 步骤 1Aa：文本分词与 BERT 特征提取

**脚本**：`GPT_SoVITS/prepare_datasets/1-get-text.py`

**输入**：
- `.list` 标注文件
- 音频文件目录

**处理流程**：
```
.list 文件
  ↓ clean_text()     文本清洗、规范化
  ↓ g2p()            文本转音素序列
  ↓ get_bert_feature() 提取 BERT 特征（1024维）
  ↓ 字级对齐 → 音素级对齐
```

**输出**：
- `{exp_dir}/2-name2text.txt`：音素序列文件
- `{exp_dir}/3-bert/*.pt`：BERT 特征张量（中文专用）

**多GPU并行**：GPU 卡号用 `-` 分隔，如 `0-1` 表示用 GPU0 和 GPU1 各跑一半数据，最后合并。

---

#### 步骤 1Ab：SSL 特征提取 + 音频重采样

**脚本**：`GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py`

**处理流程**：
```
原始音频
  ↓ 重采样到 32kHz
  ↓ CNHubert 模型提取 SSL 特征（768维）
```

**输出**：
- `{exp_dir}/4-cnhubert/*.pt`：CNHubert SSL 特征
- `{exp_dir}/5-wav32k/*.wav`：32kHz 重采样音频

**v2Pro / v2ProPlus 额外步骤**：
- 脚本：`2-get-sv.py`
- 输出：`{exp_dir}/7-sv_cn/*.pt`（说话人特征，用于更好的音色克隆）

---

#### 步骤 1Ac：语义 Token 提取

**脚本**：`GPT_SoVITS/prepare_datasets/3-get-semantic.py`

**处理流程**：
```
32kHz 音频
  ↓ SoVITS-G 编码器（预训练模型）
  ↓ 量化为离散语义 Token
```

**输出**：
- `{exp_dir}/6-name2semantic.tsv`：语义 Token 序列

**格式**：
```
item_name	semantic_audio
001	1234 5678 9012 3456 ...
002	2345 6789 0123 4567 ...
```

---

#### 一键三连智能跳过机制

`open1abc()` 会自动检查已有输出，跳过已完成的步骤：

```python
# 检查 1A 是否已完成
if not os.path.exists(path_text) or len(open(path_text).read().strip()) < 2:
    # 执行 1A

# 检查 1C 是否已完成
if not os.path.exists(path_semantic) or os.path.getsize(path_semantic) < 31:
    # 执行 1C
```

---

### 训练集目录结构（格式化完成后）

```
{exp_root}/{exp_name}/
├── 2-name2text.txt          # 音素序列（步骤1A输出）
├── 3-bert/
│   ├── 001.pt               # BERT特征（步骤1A输出）
│   └── ...
├── 4-cnhubert/
│   ├── 001.pt               # SSL特征（步骤1B输出）
│   └── ...
├── 5-wav32k/
│   ├── 001.wav              # 32kHz音频（步骤1B输出）
│   └── ...
├── 6-name2semantic.tsv      # 语义Token（步骤1C输出）
└── 7-sv_cn/                 # 说话人特征（仅v2Pro，步骤1B输出）
    ├── 001.pt
    └── ...
```

---

## 第二阶段：模型训练

### 1Ba. SoVITS 训练

**脚本**：
- v1/v2/v2Pro/v2ProPlus：`GPT_SoVITS/s2_train.py`
- v3/v4：`GPT_SoVITS/s2_train_v3_lora.py`（LoRA 微调）

**配置文件**：
- v1/v2：`GPT_SoVITS/configs/s2.json`
- v2Pro：`GPT_SoVITS/configs/s2v2Pro.json`
- v2ProPlus：`GPT_SoVITS/configs/s2v2ProPlus.json`

**关键参数**：

| 参数 | v1/v2 默认 | v3/v4 默认 | 说明 |
|------|-----------|-----------|------|
| batch_size | `显存(GB) // 2` | `显存(GB) // 8` | 每张卡的批大小 |
| total_epoch | 8 | 2 | 总训练轮数 |
| save_every_epoch | 4 | 1 | 保存频率 |
| text_low_lr_rate | 0.4 | - | 文本模块学习率权重（v1/v2专用） |
| lora_rank | - | 32 | LoRA 秩（v3/v4专用） |

**输出**：`SoVITS_weights/{version}/` 目录下的 `.pth` 权重文件

---

### 1Bb. GPT 训练

**脚本**：`GPT_SoVITS/s1_train.py`

**配置文件**：
- v1：`GPT_SoVITS/configs/s1longer.yaml`
- v2+：`GPT_SoVITS/configs/s1longer-v2.yaml`

**关键参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| batch_size | `显存(GB) // 2` | 每张卡的批大小 |
| total_epoch | 15 | 总训练轮数 |
| save_every_epoch | 5 | 保存频率 |
| if_dpo | False | 是否开启 DPO 训练（实验性） |

**训练数据来源**：
- `{exp_dir}/6-name2semantic.tsv`（语义 Token）
- `{exp_dir}/2-name2text.txt`（音素序列）

**输出**：`GPT_weights/{version}/` 目录下的 `.ckpt` 权重文件

---

## 第三阶段：推理

### 1C. 推理 WebUI

**推理模式**：

| 模式 | 脚本 | 说明 |
|------|------|------|
| 标准推理 | `inference_webui.py` | 逐句推理，稳定 |
| 加速推理 | `inference_webui_fast.py` | 批量并行，速度更快 |

**配置传递方式**（通过环境变量）：
```
gpt_path          → GPT 模型路径
sovits_path       → SoVITS 模型路径
cnhubert_base_path → CNHubert 模型路径
bert_path         → BERT 模型路径
_CUDA_VISIBLE_DEVICES → GPU 编号
```

---

## 版本对比

| 版本 | 训练方式 | 说话人特征 | 推荐场景 |
|------|---------|-----------|---------|
| v1 | 全量微调 | 无 | 基础使用 |
| v2 | 全量微调 | 无 | 通用推荐 |
| v2Pro | 全量微调 | ✅ ERes2Net | 音色克隆精度要求高 |
| v2ProPlus | 全量微调 | ✅ ERes2Net | 最高精度 |
| v3 | LoRA 微调 | 无 | 显存不足时 |
| v4 | LoRA 微调 | 无 | 显存不足时 |

---

## 快速参考：各步骤输入输出

| 步骤 | 输入 | 输出 |
|------|------|------|
| 0a UVR5 | 带伴奏音频 | 纯人声 .wav |
| 0b 切分 | 长音频 | 短片段 .wav（2-15秒） |
| 0c ASR | 短片段 .wav | .list 标注文件 |
| 0d 校对 | .list 文件 | 修正后 .list 文件 |
| 1Aa 文本 | .list + 音频目录 | 2-name2text.txt + 3-bert/*.pt |
| 1Ab SSL | .list + 音频目录 | 4-cnhubert/*.pt + 5-wav32k/*.wav |
| 1Ac 语义 | .list + 预训练SoVITS-G | 6-name2semantic.tsv |
| 1Ba SoVITS训练 | 上述所有特征 | SoVITS_weights/*.pth |
| 1Bb GPT训练 | 2-name2text + 6-name2semantic | GPT_weights/*.ckpt |
