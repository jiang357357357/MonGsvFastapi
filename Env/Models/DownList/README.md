# 模型下载说明

这个目录放的是“共享模型依赖”的下载、安装、检查脚本。

它解决的是下面这些公共模型：

- `PretrainedModels`
- `G2PWModel`
- `FunASRModels`
- `FasterWhisperModels`
- `UVR5Weights`

注意一件很重要的事：

**你自己的角色模型不在 `DownList` 里。**

角色模型通常放在：

- `Resources/Model/.../GPT/*.ckpt`
- `Resources/Model/.../SoVITS/*.pth`

也就是说，`DownList` 管的是“项目运行依赖”，不是“你的角色成品模型”。

## 哪些是必须下载的

### 1. 所有人都必须

#### `PretrainedModels`

必须下载。

用途：

- TTS 推理
- 数据处理
- 训练
- 版本切换（v1 / v2 / v2Pro / v2ProPlus / v3 / v4）

安装目标：

- `GPT_SoVITS/pretrained_models`

如果这个没有，项目大部分核心流程都跑不起来。

---

### 2. 只要你做中文 TTS，就必须

#### `G2PWModel`

**中文 TTS 必须下载。**

用途：

- 中文字音转换
- 多音字处理

安装目标：

- `GPT_SoVITS/text/G2PWModel`

如果你只做英文、日文等非中文流程，它不是首要必需项；  
但只要涉及中文文本合成，建议直接装上。

---

### 3. 你自己的角色模型也必须有

这部分**不在 `DownList` 里**，但运行时同样必需。

至少要有一组可用权重：

- GPT 权重：`*.ckpt`
- SoVITS 权重：`*.pth`

例如你当前项目里就是这类路径：

- `Resources/Model/.../GPT/...ckpt`
- `Resources/Model/.../SoVITS/...pth`

没有角色权重时，公共依赖再完整，也只能说明底座齐了，不能直接做你的角色推理。

## 哪些是按功能选装

### `FunASRModels`

按需下载，不是基础 TTS 必需。

用途：

- 中文 / 粤语 ASR
- 数据集自动转写
- 标注生成

安装目标：

- `tools/asr/models`

适合这些场景：

- 你要批量转写中文音频
- 你要给训练集自动打标

如果你只是做已有文本的 TTS 推理，可以不下。

---

### `FasterWhisperModels`

按需下载，不是基础 TTS 必需。

用途：

- 英文 / 日文 / 多语种 ASR
- 自动识别音频文本

安装目标：

- `tools/asr/models`

适合这些场景：

- 你要做英文 / 日文 / 多语音频转写
- 你要做多语种数据集准备

如果你不使用 ASR，这个可以不下。

---

### `UVR5Weights`

按需下载，不是基础 TTS 必需。

用途：

- 人声 / 伴奏分离
- 去混响
- 去回声

安装目标：

- `tools/uvr5/uvr5_weights`

适合这些场景：

- 你要从歌曲或混合音频里拆人声
- 你要清理训练音频

如果你没有做人声分离的需求，这个可以不下。

## 最小下载方案

### 方案 A：只想跑中文 TTS 推理

必须有：

1. `PretrainedModels`
2. `G2PWModel`
3. 你自己的角色模型权重

不必先下：

- `FunASRModels`
- `FasterWhisperModels`
- `UVR5Weights`

---

### 方案 B：只想跑非中文 TTS 推理

必须有：

1. `PretrainedModels`
2. 你自己的角色模型权重

通常可以后下：

- `G2PWModel`
- `FunASRModels`
- `FasterWhisperModels`
- `UVR5Weights`

---

### 方案 C：要做中文数据集整理 / 训练

建议至少有：

1. `PretrainedModels`
2. `G2PWModel`
3. 角色训练所需数据 / 权重输出目录

按功能追加：

- 要自动转写中文音频：`FunASRModels`
- 要做人声分离：`UVR5Weights`

---

### 方案 D：要做英文 / 日文 / 多语数据集整理

建议至少有：

1. `PretrainedModels`
2. 角色训练所需数据 / 权重输出目录

按功能追加：

- 要自动转写：`FasterWhisperModels`
- 要做人声分离：`UVR5Weights`

## 推荐下载顺序

推荐按这个顺序来：

1. `PretrainedModels`
2. `G2PWModel`（如果要做中文）
3. 你自己的角色模型权重
4. `FunASRModels` / `FasterWhisperModels`（按 ASR 需求）
5. `UVR5Weights`（按音频清洗需求）

## 当前目录和用途对应表

| 模块目录 | 是否基础必需 | 目标安装位置 | 用途 |
| --- | --- | --- | --- |
| `PretrainedModels` | 是 | `GPT_SoVITS/pretrained_models` | 核心预训练模型 |
| `G2PWModel` | 中文必需 | `GPT_SoVITS/text/G2PWModel` | 中文字音转换 |
| `FunASRModels` | 否 | `tools/asr/models` | 中文 / 粤语 ASR |
| `FasterWhisperModels` | 否 | `tools/asr/models` | 英文 / 日文 / 多语 ASR |
| `UVR5Weights` | 否 | `tools/uvr5/uvr5_weights` | 分离 / 去混响 / 去回声 |

## 怎么检查

每个模块目录下都有检查脚本。

例如：

```powershell
python Env/Models/DownList/PretrainedModels/check.py
python Env/Models/DownList/G2PWModel/check.py
python Env/Models/DownList/FunASRModels/check.py
python Env/Models/DownList/FasterWhisperModels/check.py
python Env/Models/DownList/UVR5Weights/check.py
```

Windows 也可以直接用：

```powershell
.\Env\Models\DownList\PretrainedModels\check.ps1
```

## 一句话结论

如果你现在问“到底先下哪些就能跑”：

**先下 `PretrainedModels`。**

如果你做中文，再下：

**`G2PWModel`。**

然后准备好你自己的角色模型权重。

剩下的 `FunASRModels`、`FasterWhisperModels`、`UVR5Weights` 都是按功能追加，不是基础推理的第一优先级。
