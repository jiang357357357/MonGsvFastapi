# MonCore 脚本开发规范

## 📋 文档信息

- **版本**: 2.0.0
- **更新日期**: 2026-04-28
- **适用范围**: MonCore项目所有PowerShell脚本
- **维护者**: 林星晚

---

## 概述

MonCore项目使用PowerShell作为主要的脚本语言，用于自动化各种运维和开发任务。本规范体系定义了脚本开发的标准和最佳实践。

### 设计原则

- **一致性**: 所有脚本遵循统一的结构和风格
- **可读性**: 清晰的注释和输出信息
- **健壮性**: 完善的错误处理和验证
- **可维护性**: 模块化设计，易于扩展
- **用户友好**: 友好的交互和提示信息

---

## 规范文档体系

### 核心规范文档

| 文档 | 描述 | 适用场景 |
|------|------|----------|
| [脚本结构规范](./脚本结构规范.md) | 定义脚本的标准结构和组织方式 | 所有PowerShell脚本 |
| [状态标识符规范](./状态标识符规范.md) | 定义脚本输出的状态标识符格式 | 进程管理、自动化脚本 |
| [输出格式规范](./输出格式规范.md) | 定义脚本输出的格式和颜色使用 | 所有PowerShell脚本 |

### 专项规范文档（待创建）

| 文档 | 描述 | 适用场景 |
|------|------|----------|
| 进程管理脚本规范 | 进程启动、停止、状态检查脚本 | start_process.ps1, stop_process.ps1, status_process.ps1 |
| 配置文件集成规范 | .monconfig 配置文件的读取和使用 | 需要读取配置的脚本 |
| 错误处理规范 | 错误处理和异常管理 | 所有PowerShell脚本 |

---

## 快速开始

### 1. 选择脚本模板
根据脚本类型选择合适的模板：

- **进程管理脚本**: 参考 [脚本结构规范](./脚本结构规范.md#特定类型脚本结构)
- **通用工具脚本**: 参考 [脚本结构规范](./脚本结构规范.md#标准脚本模板)

### 2. 实现必需组件
确保脚本包含以下必需组件：

```powershell
# 1. PowerShell 帮助注释
<#
.SYNOPSIS
    脚本简短描述
#>

# 2. 参数定义（至少包含 NoWait）
param(
    [switch]$NoWait = $false
)

# 3. 环境设置
$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# 4. 颜色定义
$ColorGreen = "Green"
# ... 其他颜色

# 5. 状态标识符输出
Write-Host "[PROCESS_NAME:$ProcessName]" -ForegroundColor $ColorCyan
Write-Host "[SERVER_STATUS:SUCCESS]" -ForegroundColor $ColorGreen
```

### 3. 遵循输出格式
使用标准的输出格式：

```powershell
# 标题
Write-Host "================================================" -ForegroundColor $ColorCyan
Write-Host "脚本标题" -ForegroundColor $ColorCyan
Write-Host "================================================" -ForegroundColor $ColorCyan

# 步骤
Write-Host "[1/3] 检查环境..." -ForegroundColor $ColorMagenta

# 状态图标
Write-Host "[✓] 操作成功" -ForegroundColor $ColorGreen
```

---

## 目录结构规范

### Scripts目录组织

```
Scripts/
├── Cmd/                # 主要启动脚本
│   ├── Start.ps1
│   └── Stop.ps1
├── Process/            # 进程管理脚本
│   ├── start_process.ps1
│   ├── status_process.ps1
│   └── stop_process.ps1
├── Venv/               # 虚拟环境管理脚本
│   ├── check_env.ps1
│   ├── install_env.ps1
│   └── remove_env.ps1
└── lib/                # 公共库和工具
    └── MonConfig.ps1
```

### 目录分类原则

| 目录 | 用途 | 示例 |
|------|------|------|
| `Cmd/` | 主要命令脚本 | 服务启动、停止 |
| `Process/` | 进程管理 | 后台进程控制 |
| `Venv/` | 环境管理 | 虚拟环境配置 |
| `lib/` | 公共库 | 配置加载器、工具函数 |

---

## 脚本命名规范

### 命名规则

1. **使用小写字母和下划线**: `start_process.ps1`
2. **动词+名词结构**: `check_env.ps1`, `install_env.ps1`
3. **清晰描述功能**: 名称应明确表达脚本用途
4. **统一后缀**: 所有PowerShell脚本使用`.ps1`后缀

### 常用动词

| 动词 | 含义 | 示例 |
|------|------|------|
| `start` | 启动 | `start_process.ps1` |
| `stop` | 停止 | `stop_process.ps1` |
| `status` | 状态查看 | `status_process.ps1` |
| `check` | 检查 | `check_env.ps1` |
| `install` | 安装 | `install_env.ps1` |
| `remove` | 删除 | `remove_env.ps1` |

---

## 最佳实践

### 1. 路径处理
```powershell
# ✓ 正确：使用Join-Path
$FilePath = Join-Path $ProjectRoot "Data\Logs\app.log"

# ✗ 错误：字符串拼接
$FilePath = "$ProjectRoot\Data\Logs\app.log"
```

### 2. 配置读取
```powershell
# ✓ 正确：从.monconfig读取
$ConfigFile = Join-Path $ProjectRoot ".monconfig"
if (Test-Path $ConfigFile) {
    $ConfigContent = Get-Content $ConfigFile -Raw -Encoding UTF8
    # 解析配置...
}
```

### 3. 错误处理
```powershell
# ✓ 正确：完整的错误处理
try {
    # 主要逻辑
} catch {
    Write-Host "[SERVER_STATUS:FAILED]" -ForegroundColor $ColorRed
    Write-Host "错误信息: $_" -ForegroundColor $ColorRed
    exit 1
}
```

### 4. 用户交互
```powershell
# ✓ 正确：支持NoWait参数
if (-not $NoWait) {
    Write-Host "按任意键退出..." -ForegroundColor $ColorGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
```

---

## 脚本检查清单

提交脚本前请确认以下事项：

### 基础要求
- [ ] 包含完整的 PowerShell 帮助注释
- [ ] 包含文件头注释
- [ ] 定义了必需的参数（至少包含 NoWait）
- [ ] 设置了错误处理和编码
- [ ] 定义了标准颜色变量

### 结构要求
- [ ] 正确计算项目根目录
- [ ] 显示了标准格式的标题
- [ ] 使用步骤提示格式
- [ ] 包含了完整的错误处理
- [ ] 支持 NoWait 参数控制用户交互

### 输出要求
- [ ] 输出了正确的状态标识符
- [ ] 使用了标准颜色和图标
- [ ] 错误信息包含解决建议
- [ ] 表格对齐正确处理中英文

### 功能要求
- [ ] 从.monconfig读取配置
- [ ] 日志记录完整
- [ ] 代码注释充分
- [ ] 测试通过

---

## 相关资源

### 参考文档
- [PowerShell官方文档](https://docs.microsoft.com/powershell/)
- [PowerShell最佳实践](https://github.com/PoshCode/PowerShellPracticeAndStyle)

### 项目文档
- [MonCore项目文档](../../../README.md)
- [配置文件规范](../../配置/MonConfig配置规范.md)

---

*文档维护: 林星晚 | 最后更新: 2026-04-28*