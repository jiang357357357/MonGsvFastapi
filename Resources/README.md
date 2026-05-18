# Resources 资源目录规范（初稿）

## 1. 文档目的

本文件用于统一 `Resources` 目录的组织方式，解决以下问题：

1. 模型资产和训练中间产物混在一起，不好管理
2. 不清楚哪些文件应该长期保留，哪些文件属于过程产物
3. 同一个角色进行多次训练时，目录容易混乱
4. 前端角色页、推理页、训练页对资源目录的理解不一致

本规范当前处于“可落地初稿”阶段，目标不是一次定死全部细节，而是先明确主干结构和命名规则。


## 2. 顶层原则

`Resources` 目录只区分两大类资源：

- `Resources/Model`：最终模型资产
- `Resources/Train`：训练工程与训练过程产物

核心原则如下：

### 2.1 Model 是长期资产

放“最终可用、可复用、可分发”的东西，例如：

- 最终 SoVITS 权重
- 最终 GPT 权重
- 角色元信息
- 情感语音样本
- 模型配置快照
- 官方底模 / 预训练模型

一句话：

> 可以直接给推理、角色管理、模型发布使用的，放到 `Model`

### 2.2 Train 是过程工程

放“为训练服务、可重建、可清理”的东西，例如：

- 原始训练音频
- 切分结果
- ASR 结果
- BERT / Hubert / semantic 特征
- checkpoint
- 日志
- eval 输出
- 临时缓存

一句话：

> 为训练流程服务的中间资源，放到 `Train`


## 3. 术语定义

为了避免“版本”这个词反复重名，文档里使用下面几个术语：

### 3.1 world

世界、作品、来源域。

例如：

- `原神`
- `崩坏：星穹铁道`
- `明日方舟`
- `Standalone`（没有世界归属时的临时或独立分类）

### 3.2 role

角色名称。

例如：

- `芙宁娜`
- `景元`
- `阿尔图罗2`

### 3.3 base_version

官方模型体系版本，即模型结构和底模体系版本。

例如：

- `v1`
- `v2`
- `v2Pro`
- `v2ProPlus`

这一层决定的是：

- 采用哪套底模
- 采用哪套训练脚本
- GPT / SoVITS 是否兼容

### 3.4 release_version

我们自己训练导出的角色版本。

例如：

- `release_001`
- `release_002`
- `release_003`

这一层用于区分：

- 同一角色多次训练结果
- 不同数据清洗策略
- 不同训练参数组合
- 不同阶段的最佳成品

### 3.5 experiment

训练实验或训练工程实例。

例如：

- `exp_001`
- `exp_20260511_001`
- `sovits_retry_001`

它属于训练过程层，而不是最终模型层。


## 4. 推荐目录结构

### 4.1 模型资产层

```text
Resources/
  Model/
    <world>/
      <role>/
        <base_version>/
          <release_version>/
            GPT/
            SoVITS/
            meta/
            emotion/
            config/
```

### 4.2 训练工程层

```text
Resources/
  Train/
    Projects/
      <world>/
        <role>/
          <base_version>/
            <experiment>/
              source/
              dataset/
              train/
              infer/
              config/
```


## 5. Model 层职责说明

`Resources/Model` 代表角色成品层。

某个 `release_version` 下建议只放下面这些内容：

### 5.1 `GPT/`

存放该成品版本导出的 GPT 权重。

例如：

- `阿尔图罗2-e20.ckpt`

### 5.2 `SoVITS/`

存放该成品版本导出的 SoVITS 权重。

例如：

- `阿尔图罗2_e20_s780.pth`

### 5.3 `meta/`

角色元信息。

例如：

- `role.json`
- `README.md`

建议记录：

- 角色名
- 展示名
- 语言
- 描述
- base_version
- release_version

### 5.4 `emotion/`

情感参考语音样本目录。

这个目录用于承载“推理阶段直接可选的情感语音样本”，不再保留抽象的 `presets/` 或 `refs/` 概念。

推荐命名规则：

```text
[情感][语言代码]文本.wav
```

例如：

```text
[开心][zh]今天真是个好天气.wav
[sad][en]I just miss you a little.wav
[通常][ja]今日はいい天気ですね.wav
```

这样做的好处：

1. 文件名同时承载“情感标签”、“语言代码”和“参考文本”
2. 前端可以直接扫描文件名生成列表
3. 不必额外维护一套松散的预设 JSON 才能使用

### 5.5 `config/`

保留该成品版本对应的关键训练配置快照。

建议至少保留：

- `s1_config.yaml`
- `s2_config_v2ProPlus.json`

注意：

这里保存的是“成品配置快照”，主要用于追溯，不一定作为唯一训练入口。


## 6. Train 层职责说明

`Resources/Train` 代表训练工程层。

训练工程以 `experiment` 为单位组织。

### 6.1 `source/`

原始训练素材。

例如：

- 原始音频
- 清洗后音频
- 原始参考文本

### 6.2 `dataset/`

预处理产物。

例如：

- `sliced/`
- `asr/`
- `2-name2text.txt`
- `3-bert/`
- `4-cnhubert/`
- `5-wav32k/`
- `6-name2semantic.tsv`
- `7-sv_cn/`
- `logs_s2_*`

### 6.3 `train/`

训练过程目录。

例如：

- `gpt/`
- `sovits/`
- `logs/`
- `ckpt/`
- `eval/`

### 6.4 `infer/`

训练工程内的临时推理目录。

例如：

- 测试输出
- 推理缓存
- 临时验证用音频

### 6.5 `config/`

该训练工程使用的配置文件。

这些配置文件应当优先指向当前 `experiment` 目录，而不是历史路径。


## 7. 为什么 Model 和 Train 必须分开

如果这两者不分开，会出现几个直接问题：

1. 不知道哪些文件能删，哪些不能删
2. 一个角色做多次训练时，目录会被中间文件污染
3. 前端“角色页”和“训练页”的职责会混在一起
4. 最终模型资产无法稳定引用

因此：

- `Model` 是角色长期资产
- `Train` 是训练流程工程

这两个概念必须解耦。


## 8. 命名规范建议

### 8.1 世界名

如果角色没有明确世界归属，当前推荐放到：

```text
Standalone
```

后续如果有更明确的归档策略，再考虑替换为：

- `__default__`
- `Unassigned`
- `Misc`

当前推荐优先使用 `Standalone`，可读性更好。

### 8.2 release_version

当前推荐格式：

```text
release_001
release_002
release_003
```

优点：

- 可读性强
- 排序稳定
- 容易和 experiment 区分

### 8.3 experiment

当前推荐格式：

```text
exp_001
exp_002
exp_003
```

如果后面要保留时间信息，也可以扩展为：

```text
exp_20260511_001
```


## 9. 当前项目中的实际示例

当前已做的试迁移示例：

### 9.1 模型成品

[Resources/Model/Standalone/阿尔图罗2/v2ProPlus/release_001](D:/code/model/MonGsvFastapi/Resources/Model/Standalone/阿尔图罗2/v2ProPlus/release_001)

当前结构：

```text
release_001/
  GPT/
  SoVITS/
  meta/
  emotion/
  config/
```

### 9.2 训练工程

[Resources/Train/Projects/Standalone/阿尔图罗2/v2ProPlus/exp_001](D:/code/model/MonGsvFastapi/Resources/Train/Projects/Standalone/阿尔图罗2/v2ProPlus/exp_001)

当前结构：

```text
exp_001/
  source/
  dataset/
  train/
  infer/
  config/
```

说明：

- 当前迁移采用的是“保守迁移”
- 新目录已经建立并复制了内容
- 原 `music/阿尔图罗2` 暂时仍保留，用于平稳过渡


## 10. 迁移原则

迁移分两步走：

### 10.1 第一步：建立新结构，不删旧目录

目标：

- 先把新目录跑通
- 避免影响现有训练与推理流程

### 10.2 第二步：后端和前端逐步切换引用

需要逐步切换：

- 训练入口读取 `Resources/Train/.../config`
- 推理入口读取 `Resources/Model/...`
- 角色页扫描 `Model`
- 训练页扫描 `Train`

### 10.3 第三步：旧目录退役

只有在新链路稳定后，才考虑：

- 归档旧 `music/*`
- 删除重复副本
- 清理中间大文件


## 11. 后续待定问题

当前仍有几个问题需要后续继续想清楚：

1. `GPT` 和 `SoVITS` 是否必须始终成对出现
2. `meta` 是否需要拆成统一规范字段
3. `emotion/` 中是否需要配套一个索引 JSON
4. 是否需要在 `Model` 层引入“当前默认 release”的概念
5. 是否需要给 `Train` 层增加统一的日志索引


## 12. 当前结论

当前最推荐的目录原则就是一句话：

- `Model` = 角色成品
- `Train` = 训练过程

当前最推荐的目录骨架是：

```text
Resources/
  Model/
    <world>/
      <role>/
        <base_version>/
          <release_version>/
            GPT/
            SoVITS/
            meta/
            emotion/
            config/

  Train/
    Projects/
      <world>/
        <role>/
          <base_version>/
            <experiment>/
              source/
              dataset/
              train/
              infer/
              config/
```

后续所有角色、训练任务、前端页面、后端接口，原则上都应围绕这套结构收敛。
