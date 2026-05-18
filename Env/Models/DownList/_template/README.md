# 模块脚本模板

这个文件夹包含通用的模块管理脚本模板。

## 文件说明

- `check.py` - 检查模块是否完整安装
- `download.py` - 从 HuggingFace 下载模块
- `delete.py` - 删除已安装的模块

## 使用方法

### 1. 创建新模块

```bash
# 复制模板到新模块目录
cp -r _template/ your_module_name/
```

### 2. 修改配置

编辑新模块目录下的脚本，修改 `CONFIG` 字典：

```python
CONFIG = {
    "name": "你的模块名称",
    "repo": "huggingface/repo-name",
    "file": "model.zip",
    "env_var": "YOUR_MODULE_PATH",
    "default_path": "path/to/module",
    "files": ["file1.txt", "dir1"],
    "extract": True,
}
```

### 3. 配置环境变量

在 `Env/.env` 文件中添加：

```env
YOUR_MODULE_PATH=path/to/module
```

### 4. 注册模块

在 `Config/App/core/config.py` 的 `MODULES` 字典中添加：

```python
MODULES = {
    "your_module_name": {"name": "你的模块名称"},
}
```

## 配置说明

### CONFIG 字段

- `name`: 模块显示名称（中文）
- `repo`: HuggingFace 仓库 ID
- `file`: 要下载的文件名（通常是 .zip）
- `env_var`: 环境变量名称（用于自定义路径）
- `default_path`: 默认安装路径（相对于项目根目录）
- `files`: 检查时需要验证的文件/目录列表
- `extract`: 是否需要解压下载的文件

## 自定义逻辑

如果需要特殊的下载或检查逻辑，可以重写相应函数：

```python
def download():
    # 自定义下载逻辑
    pass

def check():
    # 自定义检查逻辑
    pass

def delete():
    # 自定义删除逻辑
    pass
```

## 示例

参考现有模块：
- `pretrained_models/` - 标准 zip 下载解压
- `G2PWModel/` - 单个模型下载
- `nltk_data/` - 多文件下载
