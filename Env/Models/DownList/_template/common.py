#!/usr/bin/env python3
"""
通用工具函数库

提供模块管理脚本所需的公共功能：
- 项目根目录定位
- 环境变量加载
- HuggingFace 下载
- 文件检查和清理
"""
import os
import shutil
import subprocess
import sys


def find_project_root(start_path):
    """尽可能可靠地定位项目根目录（跨 Windows/Linux）。

    优先通过仓库特征文件定位（例如 pyproject.toml / .git）。
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current, "pyproject.toml")):
            return current
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.path.normpath(os.path.join(os.path.abspath(start_path), "..", "..", ".."))


def get_hf_endpoint_candidates():
    """返回 HuggingFace 下载端点候选列表（优先国内镜像，失败回退官方）。"""
    candidates = []

    env_endpoint = (os.environ.get("HF_ENDPOINT") or "").strip()
    if env_endpoint:
        candidates.append(env_endpoint.rstrip("/"))

    candidates.extend(
        [
            "https://hf-mirror.com",
            "https://huggingface.co",
        ]
    )

    seen = set()
    unique = []
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def get_progress_file_path():
    """获取进度文件路径，用于 GUI 实时显示下载进度"""
    import tempfile
    return os.path.join(tempfile.gettempdir(), "mongsv_download_progress.txt")


def write_progress_to_file(percent, downloaded, total, speed, status="downloading"):
    """将进度信息写入临时文件，供 GUI 读取显示"""
    try:
        progress_file = get_progress_file_path()
        with open(progress_file, 'w', encoding='utf-8') as f:
            f.write(f"{status}\n")
            f.write(f"{percent:.1f}\n")
            f.write(f"{downloaded}\n")
            f.write(f"{total}\n")
            f.write(f"{speed:.2f}\n")
    except:
        pass


def hf_hub_download_with_fallback(repo_id, filename, repo_type="model"):
    """使用单线程下载（优先国内源，失败回退 HF 官方），带进度条显示，并写入进度文件供 GUI 实时显示。"""
    import requests
    from tqdm import tqdm
    import time

    last_error = None
    
    # 获取 HuggingFace 缓存目录
    hf_cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    
    for endpoint in get_hf_endpoint_candidates():
        try:
            print(f"  [→] 使用端点: {endpoint}")
            
            # 构建下载 URL
            if repo_type == "model":
                url = f"{endpoint}/{repo_id}/resolve/main/{filename}"
            else:
                url = f"{endpoint}/{repo_type}s/{repo_id}/resolve/main/{filename}"
            
            # 构建本地缓存路径
            repo_folder = repo_id.replace("/", "--")
            cache_path = os.path.join(hf_cache, f"models--{repo_folder}", "snapshots", "main", filename)
            
            # 确保缓存目录存在
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            print(f"  [📥] 开始下载: {filename}")
            print(f"  [📁] 保存位置: {cache_path}")
            
            # 写入开始状态到进度文件
            write_progress_to_file(0, 0, 0, 0, "starting")
            
            # 使用 requests 下载，带进度条
            start_time = time.time()
            last_update_time = start_time
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 创建进度条
            progress = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=f"  下载进度",
                ncols=75,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            )
            
            # 下载并写入文件
            downloaded = 0
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.update(len(chunk))
                        
                        # 每 0.5 秒更新一次进度文件
                        current_time = time.time()
                        if current_time - last_update_time >= 0.5:
                            percent = (downloaded / total_size * 100) if total_size > 0 else 0
                            elapsed = current_time - start_time
                            speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
                            write_progress_to_file(percent, downloaded, total_size, speed, "downloading")
                            last_update_time = current_time
            
            progress.close()
            
            # 计算下载速度
            elapsed = time.time() - start_time
            size_mb = downloaded / (1024 * 1024)
            avg_speed = size_mb / elapsed if elapsed > 0 else 0
            
            # 写入完成状态
            write_progress_to_file(100, downloaded, total_size, avg_speed, "completed")
            
            print(f"  [✓] 下载完成: {size_mb:.2f} MB")
            print(f"  [⚡] 平均速度: {avg_speed:.2f} MB/s")
            print(f"  [⏱️] 用时: {elapsed:.1f} 秒")
            print(f"  [📂] 文件位置: {cache_path}")
            
            return cache_path
            
        except Exception as e:
            last_error = e
            write_progress_to_file(0, 0, 0, 0, f"error: {e}")
            print(f"  [!] 端点 {endpoint} 失败: {e}")
            continue

    raise last_error


def run_check_script(check_script, cwd):
    """运行模块 check.py 并用退出码判断是否已安装完整。"""
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        [sys.executable, check_script],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=60,
    )
    return result.returncode == 0


def is_model_ready(module_dir, project_root):
    """统一通过模块 check.py 判断模型是否完整可用。"""
    check_script = os.path.join(module_dir, "check.py")
    if not os.path.exists(check_script):
        return False
    return run_check_script(check_script, project_root)


def prepare_redownload(module_dir, project_root, target_path, is_dir=True):
    """下载前准备：检查通过则跳过，否则清理旧内容后继续下载。"""
    if is_model_ready(module_dir, project_root):
        print("  [=] 检查通过，跳过下载")
        return False

    if os.path.exists(target_path):
        print("  [*] 检查未通过，清理旧内容后重新下载...")
        if is_dir:
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
    return True


def _supports_unicode_output():
    """检测终端是否支持 Unicode 输出"""
    encoding = sys.stdout.encoding or os.environ.get("PYTHONIOENCODING") or "utf-8"
    sample = "✓✗"
    try:
        sample.encode(encoding)
        return True
    except Exception:
        return False


def glyph_ok():
    """返回"成功"标记字符"""
    return "✓" if _supports_unicode_output() else "OK"


def glyph_bad():
    """返回"失败"标记字符"""
    return "✗" if _supports_unicode_output() else "X"


def assume_yes():
    """检查是否设置了自动确认环境变量"""
    return (os.environ.get("DOWNLIST_ASSUME_YES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def load_env_file():
    """加载 .env 文件并设置环境变量
    
    Returns:
        tuple: (project_root, env_dir)
    """
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 查找项目根目录
    project_root = find_project_root(script_dir)

    env_candidates = [
        os.path.join(project_root, "Env", ".env"),
        os.path.join(project_root, "Code", "Env", ".env"),
        os.path.join(project_root, ".env"),
    ]

    env_path = None
    for candidate in env_candidates:
        if os.path.exists(candidate):
            env_path = candidate
            break

    env_dir = (
        os.path.dirname(env_path) if env_path else os.path.join(project_root, "Env")
    )

    if env_path:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # 只在环境变量不存在时设置，避免覆盖已有配置
                    if key not in os.environ:
                        os.environ[key] = value
    return project_root, env_dir
