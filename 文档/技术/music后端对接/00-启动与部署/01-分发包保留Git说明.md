# 分发包保留 Git 目录说明

## 背景

MonGsvFastapi 的分发包不仅用于首次交付，也可能用于客户机器上的后续维护。为了让客户现场环境可以继续从 Git 仓库拉取更新，分发包需要保留根目录下的 `.git` 目录。

如果打包时排除 `.git`，客户解压后的目录只是普通文件夹，不能直接执行 `git pull`，也不能保留分支、远程仓库、提交记录和子模块指针状态。后续更新只能重新发完整压缩包。

## 为什么保留 `.git`

保留 `.git` 的主要原因是让分发包具备持续更新能力：

1. 客户解压后仍然是一个 Git 工作区，可以直接查看当前版本。
2. 后续可以使用 `git pull` 获取增量更新，不必每次重新传完整包。
3. 出问题时可以用 `git status`、`git log`、`git diff` 判断客户现场是否改过文件。
4. 该项目包含 `Code/FastApi` 和 `Code/GptSov_Front` 两个子模块，保留 Git 信息有利于追踪根仓库和子模块版本。
5. 现场部署可以在同一目录内完成“运行包”和“代码仓库”的统一管理，减少版本来源不清的问题。

## 为什么也要保留 `.gitignore`

如果只保留 `.git`，但打包时排除了 `.gitignore`，客户解压后 Git 会认为 `.gitignore` 被删除，工作区会立即变成未清洁状态。

因此，分发包如果保留 `.git`，也应保留 `.gitignore`。这样客户解压后执行：

```powershell
git status
```

应该能看到接近干净的工作区，只剩部署现场确实产生或修改的文件。

## 当前打包配置

当前 `.monconfig` 的 `[pack] EXCLUDE_PATTERNS` 不再排除：

```text
.git
.gitignore
```

打包脚本仍会排除 `.venv`、`node_modules`、日志、临时输出、数据库、媒体目录和已有压缩包等运行时或缓存文件。

这表示分发包会保留 Git 工作区能力，但不会把本机 Python 虚拟环境和前端依赖目录一起带走。

## 客户机器更新方式

客户解压分发包后，可以在项目根目录查看版本：

```powershell
git status
git log -1 --oneline
```

如果后续需要从远程仓库更新：

```powershell
git pull
git submodule update --init --recursive
```

如果更新涉及前端代码，更新后需要重新构建前端：

```powershell
.\Script\Cmd\Win\build-frontend.cmd
```

如果更新涉及 Python 依赖，需要重新安装或同步环境：

```powershell
powershell -ExecutionPolicy Bypass -File Env\PY\install.ps1
```

离线客户机器则应优先使用随包提供的 `Env\OfflinePy` 安装脚本。

## 风险与注意事项

保留 `.git` 会带来额外风险，需要在分发前确认：

1. 压缩包会变大，因为包含 Git 历史和对象库。
2. 远程仓库地址会保留在 `.git/config` 中。
3. 如果仓库历史里曾提交过敏感信息，保留 `.git` 会把这些历史也带给客户。
4. 客户现场如果直接改代码，后续 `git pull` 可能出现冲突，需要先处理本地改动。
5. 如果客户没有 Git 或没有仓库权限，保留 `.git` 只能用于版本追踪，不能完成远程更新。

因此，这种分发方式适合长期维护、需要增量更新、并且客户有 Git 更新权限的部署场景。不适合只交付一次、希望隐藏仓库历史或不希望客户接触源码历史的场景。

## 分发前检查

打包完成后建议检查压缩包内是否包含关键 Git 文件：

```powershell
& "C:\Program Files\7-Zip\7z.exe" l ".\MonGsvFastapi_xxxxxxxx_xxxxxx.7z" .git .gitignore .gitmodules start.cmd
```

也可以解压到临时目录后检查：

```powershell
git status
git submodule status
```

如果这些命令能正常执行，说明分发包保留 Git 工作区的目标已经达成。
