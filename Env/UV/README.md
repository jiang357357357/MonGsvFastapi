# UV 包管理器管理脚本

UV 是一个极速的 Python 包和项目管理器，使用 Rust 编写，比 pip 快 10-100 倍。

## 📁 文件说明

- `check.ps1` - 检查 UV 是否已安装及版本信息
- `install.ps1` - 安装或更新 UV 包管理器
- `uninstall.ps1` - 完全卸载 UV 及其数据

## 🚀 使用方法

### 检查 UV 状态

```powershell
powershell -ExecutionPolicy Bypass -File Env\UV\check.ps1
```

### 安装 UV

```powershell
powershell -ExecutionPolicy Bypass -File Env\UV\install.ps1
```

安装完成后需要重启终端以使 PATH 环境变量生效。

### 卸载 UV

```powershell
powershell -ExecutionPolicy Bypass -File Env\UV\uninstall.ps1
```

## 📦 UV 安装位置

- **可执行文件**: `%USERPROFILE%\.local\bin\`
  - `uv.exe` - 主程序
  - `uvx.exe` - 工具运行器
  - `uvw.exe` - Windows 包装器

- **缓存目录**: 由 `uv cache dir` 命令查看
- **Python 安装**: 由 `uv python dir` 命令查看
- **工具目录**: 由 `uv tool dir` 命令查看

## 🔧 UV 常用命令

### 项目管理
```bash
# 创建新项目
uv init my-project

# 添加依赖
uv add requests

# 安装依赖
uv sync

# 运行脚本
uv run python script.py
```

### Python 版本管理
```bash
# 安装 Python 版本
uv python install 3.12

# 列出已安装的 Python
uv python list

# 设置项目 Python 版本
uv python pin 3.12
```

### 虚拟环境
```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 在虚拟环境中运行
uv run python script.py
```

### 工具管理
```bash
# 安装全局工具
uv tool install ruff

# 运行工具（无需安装）
uvx ruff check .

# 列出已安装工具
uv tool list
```

## 📚 参考资源

- [官方文档](https://docs.astral.sh/uv/)
- [GitHub 仓库](https://github.com/astral-sh/uv)
- [快速开始指南](https://docs.astral.sh/uv/getting-started/)

## ⚠️ 注意事项

1. **首次安装后需要重启终端**以使 PATH 生效
2. **网络要求**: 安装需要访问 `astral.sh` 和 GitHub
3. **权限要求**: 某些操作可能需要管理员权限
4. **防火墙**: 确保防火墙允许下载

## 🔄 更新 UV

UV 支持自我更新：

```bash
uv self update
```

或者重新运行安装脚本：

```powershell
powershell -ExecutionPolicy Bypass -File Env\UV\install.ps1
```

## 🐛 故障排除

### UV 命令未找到
- 重启终端
- 检查 PATH: `$env:Path -split ';' | Select-String '.local\bin'`
- 手动添加到 PATH: `%USERPROFILE%\.local\bin`

### 安装失败
- 检查网络连接
- 关闭防火墙/代理
- 以管理员权限运行
- 查看详细错误信息

### 卸载不完整
- 手动删除 `%USERPROFILE%\.local\bin\uv*.exe`
- 从 PATH 中移除 UV 目录
- 清理缓存目录

## 💡 为什么选择 UV？

- ⚡ **极速**: 比 pip 快 10-100 倍
- 🔒 **可靠**: 内置依赖锁定和解析
- 🎯 **简单**: 统一的命令行界面
- 🌍 **全面**: 包管理 + 项目管理 + Python 版本管理
- 💾 **高效**: 全局缓存，节省磁盘空间
- 🔧 **兼容**: 支持 pip、requirements.txt、pyproject.toml
